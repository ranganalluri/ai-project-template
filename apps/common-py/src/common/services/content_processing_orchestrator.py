"""Service layer: Pipeline orchestration for document processing."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from common.infra.storage.blob_client import BlobClientWrapper
from common.models.comparison import get_extraction_comparison_data
from common.models.document import Cu_Record, DocumentStatus, ExtractedSchema, ExtractedField, EvidenceSpan, Point
from common.models.model import DataExtractionResult
from common.services.confidence import enrich_merged_confidence_with_polygons, merge_confidence_values
from common.services.cu.content_understanding_confidence_evaluator import evaluate_confidence
from common.services.cu_record_store import CuRecordStore
from common.services.cu.cu_extractor import CuExtractor
from common.services.evidence.evidence_mapper import EvidenceMapper
from common.services.image.image_utils import convert_image_metadata_to_content_items
from common.schemas.invoice_schema import Invoice
from common.services.openai.confidence_evaluator import OpenAIConfidenceEvaluator
from common.services.openai.schema_extractor import SchemaExtractor
from common.services.pdf.pdf_image_converter import PdfImageConverter
from common.models.content_understanding import AnalyzedResult
logger = logging.getLogger(__name__)


class ContentProcessingOrchestrator:
    """Service layer: Orchestrates document processing pipeline."""

    def __init__(
        self,
        blob_client: BlobClientWrapper | None = None,
        metadata_store: CuRecordStore | None = None,
        cu_extractor: CuExtractor | None = None,
        schema_extractor: SchemaExtractor | None = None,
        pdf_converter: PdfImageConverter | None = None,
        evidence_mapper: EvidenceMapper | None = None,
    ) -> None:
        """Initialize pipeline orchestrator.

        Args:
            blob_client: Blob client wrapper. If None, creates a new one.
            metadata_store: Metadata store. If None, creates a new one.
            cu_extractor: CU extractor. If None, creates a new one.
            schema_extractor: Schema extractor. If None, creates a new one.
            pdf_converter: PDF image converter. If None, creates a new one.
            evidence_mapper: Evidence mapper. If None, creates a new one.
        """
        self.blob_client = blob_client or BlobClientWrapper()
        self.metadata_store = metadata_store or CuRecordStore()
        self.cu_extractor = cu_extractor or CuExtractor()
        self.schema_extractor = schema_extractor or SchemaExtractor()
        self.pdf_converter = pdf_converter or PdfImageConverter(blob_client=self.blob_client)
        self.evidence_mapper = evidence_mapper or EvidenceMapper()

    def process_document(
        self, meta: Cu_Record, filename: str, analyzer_id: str, doc_type: str, force: bool = False
    ) -> Cu_Record:
        """Process document through the full pipeline.

        Args:
            meta: Document metadata
            filename: Original filename
            analyzer_id: CU analyzer ID to use
            doc_type: Document type for schema extraction
            force: Force reprocessing even if schemaBlobUrl exists

        Returns:
            Updated document metadata
        """
        try:
            # Check idempotency
            if meta.schema_blob_url and not force:
                logger.info(f"Schema already exists for document {meta.id}, skipping (use force=True to reprocess)")
                return meta

            tenant_id = meta.tenant_id
            user_id = meta.user_id
            document_id = meta.id

            # Step 1: Convert PDF to images (if sourceType is PDF)
            image_metadata = None
            if meta.source_type.lower() == "pdf" and meta.original_blob_url:
                logger.info(f"Converting PDF to images for document {document_id}")
                try:
                    image_metadata = self.pdf_converter.convert_pdf_to_images(
                        pdf_blob_url=meta.original_blob_url,
                        document_id=document_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                    )
                    # Update metadata with image URLs
                    image_blob_urls = [img["blobUrl"] for img in image_metadata]
                    self.metadata_store.update_metadata(
                        document_id,
                        tenant_id,
                        {"imageBlobUrls": image_blob_urls, "updatedAt": datetime.now(UTC)},
                    )
                    logger.info(f"Converted {len(image_metadata)} pages to images")
                except Exception as e:
                    logger.warning(f"Failed to convert PDF to images: {e}. Continuing with original PDF.")
                    # Continue with original PDF if conversion fails

            # Step 2: Set status CU_PROCESSING
            logger.info(f"Starting CU processing for document {document_id}")
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {"status": DocumentStatus.CU_PROCESSING.value, "updatedAt": datetime.now(UTC)},
            )

            # Step 3: Download blob bytes and call CU extract_to_raw with bytes
            if not meta.original_blob_url:
                raise ValueError(f"original_blob_url is required for document {document_id}")

            # Download blob bytes to send directly to CU API instead of using blob URL
            logger.info(f"Downloading blob bytes for document {document_id}")
            try:
                file_bytes = self.blob_client.download_bytes_from_url(meta.original_blob_url)
                logger.info(f"Downloaded {len(file_bytes)} bytes for CU processing")
                cu_raw = self.cu_extractor.extract_to_raw(
                    analyzer_id=analyzer_id, file_bytes=file_bytes, source_type=meta.source_type
                )
            except Exception as e:
                logger.warning(f"Failed to download blob bytes, falling back to URL: {e}")
                # Fallback to URL-based approach if download fails
                cu_raw = self.cu_extractor.extract_to_raw(
                    analyzer_id=analyzer_id, input_blob_url=meta.original_blob_url, source_type=meta.source_type
                )
            cu_extracted_data = AnalyzedResult(**cu_raw)
            cu_extracted_content = cu_extracted_data.result.contents[0]
            
            # Step 4: Store CU raw JSON
            cu_blob_path = f"{tenant_id}/{user_id}/{document_id}/cu/raw.json"
            cu_blob_url = self.blob_client.upload_json("content", cu_blob_path, cu_raw)

            # Step 6: Update metadata with CU artifact URL
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {
                    "cuArtifactBlobUrl": cu_blob_url,
                    "status": DocumentStatus.CU_DONE.value,
                    "updatedAt": datetime.now(UTC),
                },
            )

            # Step 7: Set status LLM_PROCESSING
            logger.info(f"Starting LLM processing for document {document_id}")
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {"status": DocumentStatus.LLM_PROCESSING.value, "updatedAt": datetime.now(UTC)},
            )

            # Step 8: Extract CU markdown and prepare content items following test pattern (test_foundry_responses_api.py:381-397)
            # Get markdown from CU raw data (test pattern: line 373)
            cu_markdown = cu_extracted_content.markdown
            # Convert images to base64 content items
            image_content_items = []
            if image_metadata:
                logger.info(f"Converting {len(image_metadata)} images to base64 data URLs for LLM")
                image_content_items = convert_image_metadata_to_content_items(image_metadata, self.blob_client)
            
            # Build content_items with markdown and images following test pattern (lines 381-390)
            content_items: list[dict[str, Any]] = []
            if cu_markdown:
                content_items.append({
                    "type": "input_text",
                    "text": cu_markdown
                })
            if image_content_items:
                # image_content_items already have the correct format: {"type": "input_image", "image_url": "..."}
                content_items.extend(image_content_items)
            
            # Prepare schema definition following test pattern (test_foundry_responses_api.py:399-400)
            schema_definition = None
            if doc_type.lower() == "invoice":
                schema_definition = {"format": Invoice.get_json_schema_definition()}
            
            # Call SchemaExtractor with content_items (markdown + images) and schema definition
            openai_response = self.schema_extractor.extract_schema(
                image_content_items=content_items if content_items else None,
                schema_definition=schema_definition
            )
            
            # Step 8.5: Extract and parse the response following test pattern (test_foundry_responses_api.py:412-523)
            extracted_data = None
            response_text = ""
            logprobs_list: list[dict[str, Any]] = []
            
            if hasattr(openai_response, "output") and openai_response.output:
                output = openai_response.output
                if isinstance(output, list):
                    for message in output:
                        if hasattr(message, "content") and message.content:
                            for content_item in message.content:
                                # Extract text from content item (test pattern: line 428-429)
                                if hasattr(content_item, "text"):
                                    response_text = content_item.text
                                    if response_text:
                                        response_text = response_text.strip()
                                        logger.debug(f"Extracted response text: {len(response_text)} characters")
                                    
                                    # Try to parse as JSON (test pattern: line 435-446)
                                    try:
                                        # Strip only (test pattern doesn't remove markdown code blocks)
                                        cleaned_text = response_text.strip()
                                        extracted_data = json.loads(cleaned_text)
                                        logger.info("Successfully parsed JSON response")
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Could not parse response as JSON: {e}")
                                        extracted_data = {}
                                
                                # Extract logprobs from content item (test pattern: line 476-503)
                                if hasattr(content_item, "logprobs") and content_item.logprobs:
                                    logger.debug("Found logprobs in content item")
                                    
                                    # Get logprobs as list - handle different structures
                                    logprobs_data = content_item.logprobs
                                    
                                    # Handle different logprobs structures
                                    if isinstance(logprobs_data, list):
                                        logprobs_list = logprobs_data
                                    elif isinstance(logprobs_data, dict):
                                        # Check for "content" key
                                        if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                                            logprobs_list = logprobs_data["content"]
                                        else:
                                            logprobs_list = []
                                            logger.warning(f"Unexpected logprobs dict structure: {type(logprobs_data)}")
                                    else:
                                        logprobs_list = []
                                        logger.warning(f"Unexpected logprobs type: {type(logprobs_data)}")
                                    
                                    # Ensure logprobs_list is a list
                                    if not isinstance(logprobs_list, list):
                                        logprobs_list = []
                                    
                                    logger.debug(f"Extracted {len(logprobs_list)} token logprobs from content item")
            
            # Check for logprobs at response level (test pattern: line 506-523)
            if hasattr(openai_response, "logprobs") and openai_response.logprobs:
                logger.debug("Found logprobs at response level")
                if not logprobs_list:
                    logprobs_data = openai_response.logprobs
                    # Handle different logprobs structures
                    if isinstance(logprobs_data, list):
                        logprobs_list = logprobs_data
                    elif isinstance(logprobs_data, dict):
                        if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                            logprobs_list = logprobs_data["content"]
                        else:
                            logprobs_list = []
                            logger.warning("Unexpected response logprobs dict structure")
                    else:
                        logprobs_list = []
                        logger.warning(f"Unexpected response logprobs type: {type(logprobs_data)}")
            
            # Step 8.6: Run OpenAI Confidence Evaluator (test pattern: line 525-538)
            gpt_confidence_results = {}
            if extracted_data and logprobs_list and response_text:
                try:
                    logger.info("Running OpenAI confidence evaluator")
                    evaluator = OpenAIConfidenceEvaluator(model=self.schema_extractor.model)
                    gpt_confidence_results = evaluator.evaluate_confidence(
                        extract_result=extracted_data,
                        generated_text=response_text,
                        logprobs=logprobs_list
                    )
                    logger.info("OpenAI confidence evaluation completed")
                except Exception as e:
                    logger.warning(f"Failed to run OpenAI confidence evaluator: {e}. Continuing without GPT confidence.")
            else:
                logger.warning("Missing logprobs or response_text, skipping OpenAI confidence evaluation")
            
            # Step 8.7: Run CU Confidence Evaluator
            content_understanding_confidence_score = {}
            if extracted_data:
                try:
                    logger.info("Running CU confidence evaluator")
                    
                    
                    content_understanding_confidence_score = evaluate_confidence(
                        extracted_data,
                        cu_extracted_content,
                    )
                    logger.info("CU confidence evaluation completed")
                except Exception as e:
                    logger.warning(f"Failed to run CU confidence evaluator: {e}. Continuing without CU confidence.")

            # Step 8.8: Merge Confidence Values
            merged_confidence_score = {}
            if gpt_confidence_results or content_understanding_confidence_score:
                try:
                    logger.info("Merging confidence values")
                    if gpt_confidence_results and content_understanding_confidence_score:
                        merged_confidence_score = merge_confidence_values(
                            content_understanding_confidence_score,
                            gpt_confidence_results
                        )
                        # Enrich merged confidence with polygon data and page numbers from CU
                        merged_confidence_score = enrich_merged_confidence_with_polygons(
                            merged_confidence_score,
                            content_understanding_confidence_score
                        )
                    elif content_understanding_confidence_score:
                        # Only CU confidence available
                        merged_confidence_score = content_understanding_confidence_score
                    elif gpt_confidence_results:
                        # Only GPT confidence available
                        merged_confidence_score = gpt_confidence_results
                    logger.info("Confidence merging completed")
                except Exception as e:
                    logger.warning(f"Failed to merge confidence values: {e}. Using available confidence scores.")
                    merged_confidence_score = content_understanding_confidence_score or gpt_confidence_results or {}
            
            # Step 8.9: Create DataExtractionResult
            extraction_result = None
            if extracted_data:
                try:
                    logger.info("Creating DataExtractionResult")
                    
                    # Extract usage information from response if available (test pattern: line 618-629)
                    prompt_tokens = 0
                    completion_tokens = 0
                    if hasattr(openai_response, "usage"):
                        usage = openai_response.usage
                        if hasattr(usage, "prompt_tokens"):
                            prompt_tokens = usage.prompt_tokens or 0
                        if hasattr(usage, "completion_tokens"):
                            completion_tokens = usage.completion_tokens or 0
                    elif hasattr(openai_response, "usage") and isinstance(openai_response.usage, dict):
                        prompt_tokens = openai_response.usage.get("prompt_tokens", 0)
                        completion_tokens = openai_response.usage.get("completion_tokens", 0)
                    
                    # Create ExtractionComparisonData
                    # Use default threshold of 0.8 (can be made configurable)
                    confidence_threshold = 0.8
                    comparison_result = get_extraction_comparison_data(
                        actual=extracted_data,
                        confidence=merged_confidence_score,
                        threads_hold=confidence_threshold,
                    )
                    
                    # Calculate execution time (could be tracked from start, but for now set to 0)
                    execution_time = 0
                    
                    # Create DataExtractionResult
                    extraction_result = DataExtractionResult(
                        extracted_result=extracted_data,
                        confidence=merged_confidence_score,
                        comparison_result=comparison_result,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        execution_time=execution_time,
                    )
                    logger.info("DataExtractionResult created successfully")
                except Exception as e:
                    logger.warning(f"Failed to create DataExtractionResult: {e}. Continuing without final result.")
            
            # Step 8.10: Store ExtractedSchema in Blob (for API to retrieve evidence/fields)
            schema_blob_url = None
            if extracted_data:
                try:
                    logger.info("Creating and storing ExtractedSchema")
                    # Create ExtractedSchema from extracted_data
                    # The extracted_data should have a "fields" array with fieldPath, value, and evidence
                    fields_list = []
                    if "fields" in extracted_data and isinstance(extracted_data["fields"], list):
                        for field_data in extracted_data["fields"]:
                            field_path = field_data.get("fieldPath", "")
                            value = field_data.get("value")
                            evidence_spans = []
                            if "evidence" in field_data and isinstance(field_data["evidence"], list):
                                for ev_data in field_data["evidence"]:
                                    evidence_confidence = ev_data.get("confidence", 0.0)
                                    polygon_points = []
                                    if "polygon" in ev_data and isinstance(ev_data["polygon"], list):
                                        for p in ev_data["polygon"]:
                                            if isinstance(p, dict) and "x" in p and "y" in p:
                                                polygon_points.append(Point(x=p["x"], y=p["y"]))
                                    evidence_spans.append(
                                        EvidenceSpan(
                                            page=ev_data.get("page", 1),
                                            polygon=polygon_points,
                                            sourceText=ev_data.get("sourceText", ""),
                                            confidence=float(evidence_confidence),
                                        )
                                    )
                            fields_list.append(
                                ExtractedField(
                                    fieldPath=field_path,
                                    value=value,
                                    evidence=evidence_spans,
                                )
                            )
                    
                    extracted_schema = ExtractedSchema(
                        docType=doc_type,
                        fields=fields_list,
                        rawModelOutput=extracted_data,
                    )
                    
                    # Store ExtractedSchema in blob
                    schema_blob_path = f"{tenant_id}/{user_id}/{document_id}/schema/extracted.json"
                    schema_blob_url = self.blob_client.upload_json(
                        "content",
                        schema_blob_path,
                        extracted_schema.model_dump(mode="json")
                    )
                    logger.info(f"ExtractedSchema stored at: {schema_blob_url}")
                except Exception as e:
                    logger.warning(f"Failed to store ExtractedSchema: {e}. Continuing without schema URL.")
            
            # Step 8.11: Store DataExtractionResult in Blob
            result_blob_url = None
            if extraction_result:
                try:
                    logger.info("Storing DataExtractionResult in blob storage")
                    result_blob_path = f"{tenant_id}/{user_id}/{document_id}/result/extraction_result.json"
                    result_blob_url = self.blob_client.upload_json(
                        "content",
                        result_blob_path,
                        extraction_result.to_dict()
                    )
                    logger.info(f"DataExtractionResult stored at: {result_blob_url}")
                except Exception as e:
                    logger.warning(f"Failed to store DataExtractionResult in blob: {e}. Continuing without result URL.")
            
            

            # Step 12: Update metadata and set status DONE
            # Save schemaBlobUrl with ExtractedSchema URL (for API to retrieve evidence/fields)
            # Save evidenceUrl with DataExtractionResult URL (extraction_result.json)
            update_data = {
                "schemaBlobUrl": schema_blob_url,  # ExtractedSchema URL
                "evidenceUrl": result_blob_url,  # DataExtractionResult URL (extraction_result.json)
                "status": DocumentStatus.DONE.value,
                "updatedAt": datetime.now(UTC),
            }
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                update_data,
            )

            logger.info(f"Successfully processed document {document_id}")
            return self.metadata_store.get_metadata(document_id, tenant_id) or meta

        except Exception as e:
            logger.error(f"Pipeline failed for document {meta.id}: {e}")
            # Set status FAILED with error details
            error_details = {
                "message": str(e),
                "code": type(e).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            try:
                self.metadata_store.update_metadata(
                    meta.id,
                    meta.tenant_id,
                    {
                        "status": DocumentStatus.FAILED.value,
                        "error": error_details,
                        "updatedAt": datetime.now(UTC),
                    },
                )
            except Exception as update_error:
                logger.error(f"Failed to update metadata with error status: {update_error}")

            # Return metadata with error
            meta.status = DocumentStatus.FAILED
            meta.error = error_details
            return meta

