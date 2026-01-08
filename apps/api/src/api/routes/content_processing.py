"""Content processing routes for document extraction."""

import logging
import mimetypes
import os
import uuid
from datetime import UTC, datetime

from api.config import Settings, get_settings
from api.services import get_file_storage
from common.infra.storage.blob_client import BlobClientWrapper
from common.models.document import Cu_Record, DocumentStatus
from common.services.content_processing_orchestrator import ContentProcessingOrchestrator
from common.services.cu_record_store import CuRecordStore
from common.services.file_storage import FileStorage
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["content-processing"], redirect_slashes=False)


class ContentProcessingRequest(BaseModel):
    """Request model for content processing."""

    tenant_id: str
    user_id: str
    doc_type: str = "invoice"  # Document type for schema extraction
    analyzer_id: str = "prebuilt-invoice"  # CU analyzer ID
    force: bool = False  # Force reprocessing


class ContentProcessingResponse(BaseModel):
    """Response model for content processing."""

    document_id: str
    status: str
    original_blob_url: str | None = None
    schema_blob_url: str | None = None
    image_blob_urls: list[str] | None = None
    evidence: dict | None = None  # Field evidence with polygons
    page_dimensions: list[dict] | None = None  # Page dimensions: [{page: 1, width: 612, height: 792}, ...]
    error: dict | None = None


def get_content_processing_orchestrator() -> ContentProcessingOrchestrator:
    """Get content processing orchestrator dependency.

    Returns:
        ContentProcessingOrchestrator instance
    """
    return ContentProcessingOrchestrator()


def get_metadata_store() -> CuRecordStore:
    """Get metadata store dependency.

    Returns:
        CuRecordStore instance
    """
    return CuRecordStore()


@router.post("/content-processing/process", response_model=ContentProcessingResponse)
async def process_content(
    file: UploadFile = FastAPIFile(...),
    tenant_id: str = "default",
    user_id: str = "default",
    doc_type: str = "invoice",
    analyzer_id: str = "prebuilt-read",
    force: bool = False,
    file_storage: FileStorage = Depends(get_file_storage),
    orchestrator: ContentProcessingOrchestrator = Depends(get_content_processing_orchestrator),
    metadata_store: CuRecordStore = Depends(get_metadata_store),
    settings: Settings = Depends(get_settings),
) -> ContentProcessingResponse:
    """Process uploaded content (PDF, image, or audio) through the content processing pipeline.

    Args:
        file: Uploaded file (PDF, image, or audio)
        tenant_id: Tenant ID
        user_id: User ID
        doc_type: Document type for schema extraction (default: "invoice")
        analyzer_id: CU analyzer ID to use (default: "prebuilt-invoice")
        force: Force reprocessing even if already processed
        file_storage: File storage service
        orchestrator: Content processing orchestrator
        metadata_store: Metadata store
        settings: Application settings

    Returns:
        Content processing response with document ID and status
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Determine source type from file extension
        _, ext = os.path.splitext(file.filename.lower())
        source_type_map = {
            ".pdf": "pdf",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".gif": "image",
            ".bmp": "image",
            ".tiff": "image",
            ".mp3": "audio",
            ".wav": "audio",
            ".m4a": "audio",
            ".ogg": "audio",
        }
        source_type = source_type_map.get(ext, "unknown")
        if source_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Supported types: PDF, images (png, jpg, etc.), audio (mp3, wav, etc.)",
            )

        # Read file content
        content = await file.read()

        # Generate document ID
        document_id = str(uuid.uuid4())

        # Upload to blob storage
        blob_client = BlobClientWrapper()
        blob_path = f"{tenant_id}/{user_id}/{document_id}/original/{file.filename}"
        original_blob_url = blob_client.upload_bytes(
            container="content",
            blob_path=blob_path,
            data=content,
            content_type=file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream",
        )

        logger.info("Uploaded file to blob: %s", original_blob_url)

        # Create Cosmos record
        # Use Python field names (not aliases) when creating with keyword arguments
        meta = Cu_Record(
            id=document_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_type=source_type,
            original_blob_url=original_blob_url,
            status=DocumentStatus.RECEIVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Store metadata
        created_meta = metadata_store.create_metadata(meta)
        logger.info("Created metadata record for document: %s", document_id)

        # Process document through pipeline
        try:
            result = orchestrator.process_document(
                meta=created_meta,
                filename=file.filename,
                analyzer_id=analyzer_id,
                doc_type=doc_type,
                force=force,
            )

            # Load evidence and page dimensions if available
            evidence = None
            page_dimensions = None
            if result.status == DocumentStatus.DONE:
                try:
                    # Load evidence.json
                    evidence_path = f"{tenant_id}/{user_id}/{result.id}/schema/evidence.json"
                    evidence = blob_client.download_json("content", evidence_path)
                except Exception as e:
                    logger.warning("Failed to load evidence.json: %s", e)

                try:
                    # Load CU artifact to get page dimensions
                    if result.cu_artifact_blob_url:
                        # Extract blob path from URL
                        from urllib.parse import urlparse
                        parsed_url = urlparse(result.cu_artifact_blob_url)
                        # Path format: /container/path/to/file
                        path_parts = parsed_url.path.lstrip("/").split("/", 1)
                        if len(path_parts) == 2:
                            container_name = path_parts[0]
                            blob_path = path_parts[1]
                            cu_artifact = blob_client.download_json(container_name, blob_path)
                            
                            # Extract page dimensions from CU artifact
                            if "pages" in cu_artifact:
                                page_dimensions = [
                                    {
                                        "page": page.get("pageNumber", i + 1),
                                        "width": page.get("width", 612.0),  # Default US Letter width
                                        "height": page.get("height", 792.0),  # Default US Letter height
                                    }
                                    for i, page in enumerate(cu_artifact["pages"])
                                ]
                            elif "analyzeResult" in cu_artifact and "pages" in cu_artifact["analyzeResult"]:
                                # Alternative structure
                                page_dimensions = [
                                    {
                                        "page": page.get("pageNumber", i + 1),
                                        "width": page.get("width", 612.0),
                                        "height": page.get("height", 792.0),
                                    }
                                    for i, page in enumerate(cu_artifact["analyzeResult"]["pages"])
                                ]
                except Exception as e:
                    logger.warning("Failed to load page dimensions: %s", e)

            return ContentProcessingResponse(
                document_id=result.id,
                status=result.status.value,
                original_blob_url=result.original_blob_url,
                schema_blob_url=result.schema_blob_url,
                image_blob_urls=result.image_blob_urls,
                evidence=evidence,
                page_dimensions=page_dimensions,
                error=result.error,
            )
        except Exception as e:
            logger.error("Error processing document %s: %s", document_id, e, exc_info=True)
            # Update metadata with error
            try:
                error_meta = metadata_store.get_metadata(document_id, tenant_id)
                if error_meta:
                    error_meta.status = DocumentStatus.FAILED
                    error_meta.error = {
                        "message": str(e),
                        "code": type(e).__name__,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    metadata_store.update_metadata(
                        document_id,
                        tenant_id,
                        {
                            "status": DocumentStatus.FAILED.value,
                            "error": error_meta.error,
                            "updatedAt": datetime.now(UTC),
                        },
                    )
            except Exception as update_error:
                logger.error("Failed to update metadata with error: %s", update_error)

            return ContentProcessingResponse(
                document_id=document_id,
                status=DocumentStatus.FAILED.value,
                original_blob_url=original_blob_url,
                error={
                    "message": str(e),
                    "code": type(e).__name__,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in process_content: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content processing failed: {e!s}")


@router.get("/content-processing/{document_id}", response_model=ContentProcessingResponse)
async def get_processing_status(
    document_id: str,
    tenant_id: str = "default",
    metadata_store: CuRecordStore = Depends(get_metadata_store),
) -> ContentProcessingResponse:
    """Get content processing status for a document.

    Args:
        document_id: Document ID
        tenant_id: Tenant ID
        metadata_store: Metadata store

    Returns:
        Content processing response with current status
    """
    try:
        meta = metadata_store.get_metadata(document_id, tenant_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # Load evidence and page dimensions if available
        evidence = None
        page_dimensions = None
        blob_client = BlobClientWrapper()
        
        if meta.status == DocumentStatus.DONE:
            try:
                # Load evidence.json
                evidence_path = f"{tenant_id}/{document_id}/schema/evidence.json"
                evidence = blob_client.download_json("content", evidence_path)
            except Exception as e:
                logger.warning("Failed to load evidence.json: %s", e)

            try:
                # Load CU artifact to get page dimensions
                if meta.cu_artifact_blob_url:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(meta.cu_artifact_blob_url)
                    path_parts = parsed_url.path.lstrip("/").split("/", 1)
                    if len(path_parts) == 2:
                        container_name = path_parts[0]
                        blob_path = path_parts[1]
                        cu_artifact = blob_client.download_json(container_name, blob_path)
                        
                        # Extract page dimensions from CU artifact
                        if "pages" in cu_artifact:
                            page_dimensions = [
                                {
                                    "page": page.get("pageNumber", i + 1),
                                    "width": page.get("width", 612.0),
                                    "height": page.get("height", 792.0),
                                }
                                for i, page in enumerate(cu_artifact["pages"])
                            ]
                        elif "analyzeResult" in cu_artifact and "pages" in cu_artifact["analyzeResult"]:
                            page_dimensions = [
                                {
                                    "page": page.get("pageNumber", i + 1),
                                    "width": page.get("width", 612.0),
                                    "height": page.get("height", 792.0),
                                }
                                for i, page in enumerate(cu_artifact["analyzeResult"]["pages"])
                            ]
            except Exception as e:
                logger.warning("Failed to load page dimensions: %s", e)

        return ContentProcessingResponse(
            document_id=meta.id,
            status=meta.status.value,
            original_blob_url=meta.original_blob_url,
            schema_blob_url=meta.schema_blob_url,
            image_blob_urls=meta.image_blob_urls,
            evidence=evidence,
            page_dimensions=page_dimensions,
            error=meta.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting processing status: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {e!s}")

