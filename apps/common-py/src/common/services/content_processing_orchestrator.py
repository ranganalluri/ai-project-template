"""Service layer: Pipeline orchestration for document processing."""

import logging
from datetime import UTC, datetime

from common.infra.storage.blob_client import BlobClientWrapper
from common.models.document import Cu_Record, DocumentStatus
from common.services.cu_record_store import CuRecordStore
from common.services.cu.cu_extractor import CuExtractor
from common.services.evidence.evidence_mapper import EvidenceMapper
from common.services.image.image_utils import convert_image_metadata_to_content_items
from common.services.openai.schema_extractor import SchemaExtractor
from common.services.pdf.pdf_image_converter import PdfImageConverter

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
        content_container: str = "content",
    ) -> None:
        """Initialize pipeline orchestrator.

        Args:
            blob_client: Blob client wrapper. If None, creates a new one.
            metadata_store: Metadata store. If None, creates a new one.
            cu_extractor: CU extractor. If None, creates a new one.
            schema_extractor: Schema extractor. If None, creates a new one.
            pdf_converter: PDF image converter. If None, creates a new one.
            evidence_mapper: Evidence mapper. If None, creates a new one.
            content_container: Container name for content storage (default: "content")
        """
        self.blob_client = blob_client or BlobClientWrapper()
        self.metadata_store = metadata_store or CuRecordStore()
        self.cu_extractor = cu_extractor or CuExtractor()
        self.schema_extractor = schema_extractor or SchemaExtractor()
        self.pdf_converter = pdf_converter or PdfImageConverter(blob_client=self.blob_client)
        self.evidence_mapper = evidence_mapper or EvidenceMapper()
        self.content_container = content_container

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

            # Step 4: Store CU raw JSON
            cu_blob_path = f"{tenant_id}/{user_id}/{document_id}/cu/raw.json"
            cu_blob_url = self.blob_client.upload_json(self.content_container, cu_blob_path, cu_raw)

            # Step 5: Normalize CU output
            cu_normalized = self.cu_extractor.normalize(cu_raw)

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

            # Step 8: Convert images to base64 content items and call SchemaExtractor
            image_content_items = None
            if image_metadata:
                logger.info(f"Converting {len(image_metadata)} images to base64 data URLs for LLM")
                image_content_items = convert_image_metadata_to_content_items(image_metadata, self.blob_client)
            
            extracted_schema, evidence_json = self.schema_extractor.extract_schema(
                cu_normalized=cu_normalized, doc_type=doc_type, image_content_items=image_content_items
            )

            # Step 9: Map evidence to CU polygons
            if image_metadata:
                logger.info(f"Mapping evidence to CU polygons for document {document_id}")
                extracted_schema = self.evidence_mapper.map_evidence_to_cu_polygons(
                    extracted_schema=extracted_schema,
                    cu_normalized=cu_normalized,
                    image_metadata=image_metadata,
                )
                # Update evidence_json with mapped polygons
                evidence_json = {
                    "fields": [
                        {
                            "fieldPath": field.fieldPath,
                            "evidence": [
                                {
                                    "page": ev.page,
                                    "polygon": [{"x": p.x, "y": p.y} for p in ev.polygon],
                                    "sourceText": ev.sourceText,
                                    "confidence": ev.confidence,
                                }
                                for ev in field.evidence
                            ],
                        }
                        for field in extracted_schema.fields
                    ]
                }

            # Step 10: Store extracted schema and evidence
            schema_blob_path = f"{tenant_id}/{user_id}/{document_id}/schema/extracted.json"
            schema_blob_url = self.blob_client.upload_json(
                self.content_container, schema_blob_path, extracted_schema.model_dump(mode="json")
            )

            evidence_blob_path = f"{tenant_id}/{user_id}/{document_id}/schema/evidence.json"
            self.blob_client.upload_json(self.content_container, evidence_blob_path, evidence_json)

            # Step 11: Update metadata and set status DONE
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {
                    "schemaBlobUrl": schema_blob_url,
                    "status": DocumentStatus.DONE.value,
                    "updatedAt": datetime.now(UTC),
                },
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

