"""Service layer: Pipeline orchestration for document processing."""

import logging
from datetime import UTC, datetime

from common.infra.storage.blob_client import BlobClientWrapper
from common.models.document import DocumentMetadata, DocumentStatus
from common.services.cosmos_metadata_store import CosmosMetadataStore
from common.services.cu.cu_extractor import CuExtractor
from common.services.openai.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Service layer: Orchestrates document processing pipeline."""

    def __init__(
        self,
        blob_client: BlobClientWrapper | None = None,
        metadata_store: CosmosMetadataStore | None = None,
        cu_extractor: CuExtractor | None = None,
        schema_extractor: SchemaExtractor | None = None,
        content_container: str = "content",
    ) -> None:
        """Initialize pipeline orchestrator.

        Args:
            blob_client: Blob client wrapper. If None, creates a new one.
            metadata_store: Metadata store. If None, creates a new one.
            cu_extractor: CU extractor. If None, creates a new one.
            schema_extractor: Schema extractor. If None, creates a new one.
            content_container: Container name for content storage (default: "content")
        """
        self.blob_client = blob_client or BlobClientWrapper()
        self.metadata_store = metadata_store or CosmosMetadataStore()
        self.cu_extractor = cu_extractor or CuExtractor()
        self.schema_extractor = schema_extractor or SchemaExtractor()
        self.content_container = content_container

    def process_document(
        self, meta: DocumentMetadata, filename: str, analyzer_id: str, doc_type: str, force: bool = False
    ) -> DocumentMetadata:
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
            if meta.schemaBlobUrl and not force:
                logger.info(f"Schema already exists for document {meta.id}, skipping (use force=True to reprocess)")
                return meta

            tenant_id = meta.tenantId
            user_id = meta.userId
            document_id = meta.id

            # Step 1: Set status CU_PROCESSING
            logger.info(f"Starting CU processing for document {document_id}")
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {"status": DocumentStatus.CU_PROCESSING.value, "updatedAt": datetime.now(UTC)},
            )

            # Step 2: Call CU extract_to_raw
            if not meta.originalBlobUrl:
                raise ValueError(f"originalBlobUrl is required for document {document_id}")

            cu_raw = self.cu_extractor.extract_to_raw(
                input_blob_url=meta.originalBlobUrl, analyzer_id=analyzer_id, source_type=meta.sourceType
            )

            # Step 3: Store CU raw JSON
            cu_blob_path = f"{tenant_id}/{user_id}/{document_id}/cu/raw.json"
            cu_blob_url = self.blob_client.upload_json(self.content_container, cu_blob_path, cu_raw)

            # Step 4: Normalize CU output
            cu_normalized = self.cu_extractor.normalize(cu_raw)

            # Step 5: Update metadata with CU artifact URL
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {
                    "cuArtifactBlobUrl": cu_blob_url,
                    "status": DocumentStatus.CU_DONE.value,
                    "updatedAt": datetime.now(UTC),
                },
            )

            # Step 6: Set status LLM_PROCESSING
            logger.info(f"Starting LLM processing for document {document_id}")
            self.metadata_store.update_metadata(
                document_id,
                tenant_id,
                {"status": DocumentStatus.LLM_PROCESSING.value, "updatedAt": datetime.now(UTC)},
            )

            # Step 7: Call SchemaExtractor
            extracted_schema, evidence_json = self.schema_extractor.extract_schema(
                cu_normalized=cu_normalized, doc_type=doc_type
            )

            # Step 8: Store extracted schema and evidence
            schema_blob_path = f"{tenant_id}/{user_id}/{document_id}/schema/extracted.json"
            schema_blob_url = self.blob_client.upload_json(
                self.content_container, schema_blob_path, extracted_schema.model_dump(mode="json")
            )

            evidence_blob_path = f"{tenant_id}/{user_id}/{document_id}/schema/evidence.json"
            self.blob_client.upload_json(self.content_container, evidence_blob_path, evidence_json)

            # Step 9: Update metadata and set status DONE
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
                    meta.tenantId,
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

