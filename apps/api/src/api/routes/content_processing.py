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
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
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


def denormalize_polygon(polygon_points: list, page_num: int, page_dimensions: list[dict] | None) -> list:
    """Convert normalized polygon coordinates (0-1 range) to CU points using page dimensions.
    
    Args:
        polygon_points: List of polygon points with x, y coordinates (normalized 0-1 or CU points)
        page_num: Page number (1-indexed)
        page_dimensions: List of page dimension dicts with keys: page, width, height
    
    Returns:
        List of denormalized polygon points in CU points format
    """
    if not polygon_points or not page_dimensions:
        return polygon_points
    
    # Find page dimensions for this page
    page_dim = None
    for pd in page_dimensions:
        if pd.get("page") == page_num:
            page_dim = pd
            break
    
    if not page_dim:
        logger.warning("No page dimensions found for page %d, keeping coordinates as-is", page_num)
        return polygon_points
    
    page_width = page_dim.get("width")
    page_height = page_dim.get("height")
    
    if not page_width or not page_height:
        logger.warning("Invalid page dimensions for page %d, keeping coordinates as-is", page_num)
        return polygon_points
    
    # Check if coordinates are normalized (0-1 range)
    # If all x and y values are between 0 and 1, they're normalized
    is_normalized = all(
        0 <= p.get("x", 0) <= 1 and 0 <= p.get("y", 0) <= 1
        for p in polygon_points
        if isinstance(p, dict) and "x" in p and "y" in p
    )
    
    if not is_normalized:
        # Already in CU points format, return as-is
        return polygon_points
    
    # Denormalize: multiply by page dimensions
    denormalized = []
    for point in polygon_points:
        if isinstance(point, dict) and "x" in point and "y" in point:
            denormalized.append({
                "x": float(point["x"]) * page_width,
                "y": float(point["y"]) * page_height,
            })
        else:
            denormalized.append(point)
    
    logger.debug("Denormalized polygon for page %d: %d points", page_num, len(polygon_points))
    return denormalized


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
                # Load page dimensions first (needed for polygon denormalization)
                try:
                    # Load CU artifact to get page dimensions
                    if result.cu_artifact_blob_url:
                        # Use BlobClientWrapper's method to extract container and blob path
                        container_name, blob_path = blob_client._extract_blob_path_from_url(result.cu_artifact_blob_url)
                        cu_artifact = blob_client.download_json(container_name, blob_path)
                        
                        # Extract page dimensions from CU artifact
                        # Try different possible structures
                        pages_data = None
                        
                        # Structure 1: Direct "pages" key
                        if "pages" in cu_artifact and isinstance(cu_artifact["pages"], list):
                            pages_data = cu_artifact["pages"]
                        # Structure 2: "analyzeResult.pages"
                        elif "analyzeResult" in cu_artifact and "pages" in cu_artifact["analyzeResult"]:
                            pages_data = cu_artifact["analyzeResult"]["pages"]
                        # Structure 3: AnalyzedResult structure - "result.contents[0].pages"
                        elif "result" in cu_artifact and "contents" in cu_artifact["result"]:
                            contents = cu_artifact["result"]["contents"]
                            if contents and len(contents) > 0 and "pages" in contents[0]:
                                pages_data = contents[0]["pages"]
                        
                        if pages_data:
                            page_dimensions = []
                            for i, page in enumerate(pages_data):
                                page_num = page.get("pageNumber")
                                if page_num is None:
                                    page_num = i + 1
                                width = page.get("width")
                                height = page.get("height")
                                # Only add if we have valid dimensions
                                if width is not None and height is not None:
                                    page_dimensions.append({
                                        "page": int(page_num),
                                        "width": float(width),
                                        "height": float(height),
                                    })
                            if page_dimensions:
                                logger.info(f"Extracted {len(page_dimensions)} page dimensions from CU artifact")
                except Exception as e:
                    logger.warning("Failed to load page dimensions from CU artifact: %s", e, exc_info=True)
                
                # Fallback: Try to get page dimensions from metrics if available
                if not page_dimensions and result.metrics:
                    try:
                        if "image_metadata" in result.metrics and isinstance(result.metrics["image_metadata"], list):
                            page_dimensions = [
                                {
                                    "page": img.get("page", i + 1),
                                    "width": float(img.get("width", 612.0)),
                                    "height": float(img.get("height", 792.0)),
                                }
                                for i, img in enumerate(result.metrics["image_metadata"])
                                if isinstance(img, dict) and "width" in img and "height" in img
                            ]
                            if page_dimensions:
                                logger.info(f"Extracted {len(page_dimensions)} page dimensions from metrics")
                    except Exception as e:
                        logger.warning("Failed to load page dimensions from metrics: %s", e)
                
                try:
                    # Load DataExtractionResult and convert to ExtractedSchema format
                    if result.evidence_url:
                        container_name, blob_path = blob_client._extract_blob_path_from_url(result.evidence_url)
                        extraction_result = blob_client.download_json(container_name, blob_path)
                        
                        # Convert comparison_result.items to fields format (same logic as GET endpoint)
                        if extraction_result and "comparison_result" in extraction_result:
                            comparison_result = extraction_result.get("comparison_result", {})
                            items = comparison_result.get("items", [])
                            
                            fields = []
                            for item in items:
                                field_name = item.get("Field", "")
                                extracted_value = item.get("Extracted")
                                confidence_str = item.get("Confidence", "0%")
                                polygon_data = item.get("Polygon")
                                page_number = item.get("PageNumber", 0)
                                
                                # Convert confidence string to float
                                confidence_float = 0.0
                                if confidence_str and isinstance(confidence_str, str):
                                    try:
                                        confidence_float = float(confidence_str.rstrip("%")) / 100.0
                                    except (ValueError, AttributeError):
                                        confidence_float = 0.0
                                
                                # Extract polygon points
                                polygon_points = []
                                if polygon_data:
                                    if isinstance(polygon_data, dict) and "combined_polygon" in polygon_data:
                                        combined_poly = polygon_data["combined_polygon"]
                                        for point in combined_poly:
                                            if isinstance(point, dict) and "x" in point and "y" in point:
                                                polygon_points.append({"x": point["x"], "y": point["y"]})
                                            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                                                polygon_points.append({"x": float(point[0]), "y": float(point[1])})
                                    elif isinstance(polygon_data, list):
                                        for point in polygon_data:
                                            if isinstance(point, dict) and "x" in point and "y" in point:
                                                polygon_points.append({"x": point["x"], "y": point["y"]})
                                            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                                                polygon_points.append({"x": float(point[0]), "y": float(point[1])})
                                
                                # Handle None case: if page_number is None or 0, default to page 1
                                if page_number is None:
                                    page = 1
                                elif page_number > 0:
                                    page = page_number
                                else:
                                    page = 1
                                
                                # Denormalize polygon coordinates if they're normalized (0-1 range)
                                if polygon_points:
                                    polygon_points = denormalize_polygon(polygon_points, page, page_dimensions)
                                
                                evidence_spans = []
                                if polygon_points or extracted_value:
                                    evidence_spans.append({
                                        "page": page,
                                        "polygon": polygon_points,
                                        "sourceText": str(extracted_value) if extracted_value is not None else "",
                                        "confidence": confidence_float,
                                    })
                                
                                if evidence_spans or extracted_value is not None:
                                    fields.append({
                                        "fieldPath": field_name,
                                        "value": extracted_value,
                                        "evidence": evidence_spans,
                                    })
                            
                            evidence = {"fields": fields} if fields else None
                        elif extraction_result and "fields" in extraction_result:
                            evidence = {"fields": extraction_result["fields"]}
                        else:
                            evidence = None
                    else:
                        evidence = None
                except Exception as e:
                    logger.warning("Failed to load extraction result: %s", e)
                    evidence = None
                
                # Page dimensions already loaded above
                    try:
                        if "image_metadata" in result.metrics and isinstance(result.metrics["image_metadata"], list):
                            page_dimensions = [
                                {
                                    "page": img.get("page", i + 1),
                                    "width": float(img.get("width", 612.0)),
                                    "height": float(img.get("height", 792.0)),
                                }
                                for i, img in enumerate(result.metrics["image_metadata"])
                                if isinstance(img, dict) and "width" in img and "height" in img
                            ]
                            if page_dimensions:
                                logger.info(f"Extracted {len(page_dimensions)} page dimensions from metrics")
                    except Exception as e:
                        logger.warning("Failed to load page dimensions from metrics: %s", e)

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
            # Load page dimensions first (needed for polygon denormalization)
            try:
                # Load CU artifact to get page dimensions
                if meta.cu_artifact_blob_url:
                    # Use BlobClientWrapper's method to extract container and blob path
                    container_name, blob_path = blob_client._extract_blob_path_from_url(meta.cu_artifact_blob_url)
                    cu_artifact = blob_client.download_json(container_name, blob_path)
                    
                    # Extract page dimensions from CU artifact
                    # Try different possible structures
                    pages_data = None
                    
                    # Structure 1: Direct "pages" key
                    if "pages" in cu_artifact and isinstance(cu_artifact["pages"], list):
                        pages_data = cu_artifact["pages"]
                    # Structure 2: "analyzeResult.pages"
                    elif "analyzeResult" in cu_artifact and "pages" in cu_artifact["analyzeResult"]:
                        pages_data = cu_artifact["analyzeResult"]["pages"]
                    # Structure 3: AnalyzedResult structure - "result.contents[0].pages"
                    elif "result" in cu_artifact and "contents" in cu_artifact["result"]:
                        contents = cu_artifact["result"]["contents"]
                        if contents and len(contents) > 0 and "pages" in contents[0]:
                            pages_data = contents[0]["pages"]
                    
                    if pages_data:
                        page_dimensions = []
                        for i, page in enumerate(pages_data):
                            page_num = page.get("pageNumber")
                            if page_num is None:
                                page_num = i + 1
                            width = page.get("width")
                            height = page.get("height")
                            # Only add if we have valid dimensions
                            if width is not None and height is not None:
                                page_dimensions.append({
                                    "page": int(page_num),
                                    "width": float(width),
                                    "height": float(height),
                                })
                        if page_dimensions:
                            logger.info(f"Extracted {len(page_dimensions)} page dimensions from CU artifact")
            except Exception as e:
                logger.warning("Failed to load page dimensions from CU artifact: %s", e, exc_info=True)
            
            # Fallback: Try to get page dimensions from metrics if available
            if not page_dimensions and meta.metrics:
                try:
                    if "image_metadata" in meta.metrics and isinstance(meta.metrics["image_metadata"], list):
                        page_dimensions = [
                            {
                                "page": img.get("page", i + 1),
                                "width": float(img.get("width", 612.0)),
                                "height": float(img.get("height", 792.0)),
                            }
                            for i, img in enumerate(meta.metrics["image_metadata"])
                            if isinstance(img, dict) and "width" in img and "height" in img
                        ]
                        if page_dimensions:
                            logger.info(f"Extracted {len(page_dimensions)} page dimensions from metrics")
                except Exception as e:
                    logger.warning("Failed to load page dimensions from metrics: %s", e)
            
            try:
                # Load DataExtractionResult from evidence_url and convert to ExtractedSchema format
                logger.info(f"Loading evidence for document {document_id}. evidence_url: {meta.evidence_url}, schema_blob_url: {meta.schema_blob_url}")
                if meta.evidence_url:
                    # Use BlobClientWrapper's method to extract container and blob path
                    container_name, blob_path = blob_client._extract_blob_path_from_url(meta.evidence_url)
                    logger.info(f"Downloading extraction result from {container_name}/{blob_path}")
                    extraction_result = blob_client.download_json(container_name, blob_path)
                    logger.info(f"Downloaded extraction result. Has comparison_result: {'comparison_result' in extraction_result if extraction_result else False}")
                    
                    # Convert DataExtractionResult.comparison_result.items to ExtractedSchema.fields format
                    if extraction_result and "comparison_result" in extraction_result:
                        comparison_result = extraction_result.get("comparison_result", {})
                        items = comparison_result.get("items", [])
                        logger.info(f"Found {len(items)} items in comparison_result")
                        
                        fields = []
                        for item in items:
                            field_name = item.get("Field", "")
                            extracted_value = item.get("Extracted")
                            confidence_str = item.get("Confidence", "0%")
                            polygon_data = item.get("Polygon")
                            page_number = item.get("PageNumber", 0)
                            
                            # Convert confidence string (e.g., "99.50%") to float (0.995)
                            confidence_float = 0.0
                            if confidence_str and isinstance(confidence_str, str):
                                try:
                                    confidence_float = float(confidence_str.rstrip("%")) / 100.0
                                except (ValueError, AttributeError):
                                    confidence_float = 0.0
                            
                            # Extract polygon points from polygon_data
                            polygon_points = []
                            if polygon_data:
                                # Handle different polygon structures
                                if isinstance(polygon_data, dict):
                                    # Check for combined_polygon
                                    if "combined_polygon" in polygon_data and isinstance(polygon_data["combined_polygon"], list):
                                        combined_poly = polygon_data["combined_polygon"]
                                        for point in combined_poly:
                                            if isinstance(point, dict) and "x" in point and "y" in point:
                                                polygon_points.append({"x": point["x"], "y": point["y"]})
                                            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                                                polygon_points.append({"x": float(point[0]), "y": float(point[1])})
                                    # Fallback to direct polygon array
                                    elif isinstance(polygon_data, list):
                                        for point in polygon_data:
                                            if isinstance(point, dict) and "x" in point and "y" in point:
                                                polygon_points.append({"x": point["x"], "y": point["y"]})
                                            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                                                polygon_points.append({"x": float(point[0]), "y": float(point[1])})
                                elif isinstance(polygon_data, list):
                                    for point in polygon_data:
                                        if isinstance(point, dict) and "x" in point and "y" in point:
                                            polygon_points.append({"x": point["x"], "y": point["y"]})
                                        elif isinstance(point, (list, tuple)) and len(point) >= 2:
                                            polygon_points.append({"x": float(point[0]), "y": float(point[1])})
                            
                            # Convert page number from 0-based to 1-based (0 means page 1)
                            # Handle None case: if page_number is None or 0, default to page 1
                            if page_number is None:
                                page = 1
                            elif page_number > 0:
                                page = page_number
                            else:
                                page = 1
                            
                            # Denormalize polygon coordinates if they're normalized (0-1 range)
                            if polygon_points:
                                polygon_points = denormalize_polygon(polygon_points, page, page_dimensions)
                            
                            # Create evidence span
                            evidence_spans = []
                            if polygon_points or extracted_value:
                                evidence_spans.append({
                                    "page": page,
                                    "polygon": polygon_points,
                                    "sourceText": str(extracted_value) if extracted_value is not None else "",
                                    "confidence": confidence_float,
                                })
                            
                            # Always add field if it has a value or field name (even without evidence)
                            if field_name or extracted_value is not None:
                                fields.append({
                                    "fieldPath": field_name,
                                    "value": extracted_value,
                                    "evidence": evidence_spans,  # Can be empty array
                                })
                        
                        evidence = {"fields": fields} if fields else None
                        if not evidence:
                            logger.warning(f"No fields created from {len(items)} items. Check item structure.")
                        logger.info(f"Converted {len(fields)} fields to evidence format")
                    elif extraction_result and "fields" in extraction_result:
                        # Fallback: if it's already in ExtractedSchema format
                        logger.info("Extraction result already in ExtractedSchema format")
                        evidence = {"fields": extraction_result["fields"]}
                    else:
                        logger.warning(f"Extraction result missing comparison_result and fields. Keys: {list(extraction_result.keys()) if extraction_result else 'None'}")
                        evidence = None
                elif meta.schema_blob_url:
                    # Fallback: try loading from schema_blob_url (ExtractedSchema format)
                    logger.info(f"Loading from schema_blob_url: {meta.schema_blob_url}")
                    container_name, blob_path = blob_client._extract_blob_path_from_url(meta.schema_blob_url)
                    extracted_schema = blob_client.download_json(container_name, blob_path)
                    if extracted_schema and "fields" in extracted_schema:
                        logger.info(f"Loaded {len(extracted_schema.get('fields', []))} fields from schema")
                        evidence = {"fields": extracted_schema["fields"]}
                    else:
                        logger.warning(f"Schema missing fields. Keys: {list(extracted_schema.keys()) if extracted_schema else 'None'}")
                        evidence = None
                else:
                    logger.warning(f"No evidence_url or schema_blob_url available for document {document_id}")
                    evidence = None
            except Exception as e:
                logger.error("Failed to load extraction result for evidence: %s", e, exc_info=True)
                evidence = None

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


@router.get("/content-processing/{document_id}/original")
async def get_original_document(
    document_id: str,
    tenant_id: str = "default",
    metadata_store: CuRecordStore = Depends(get_metadata_store),
) -> Response:
    """Get the original document (PDF/image) from blob storage.
    
    This endpoint proxies the blob storage URL to serve the document
    to the UI without requiring direct blob storage access.

    Args:
        document_id: Document ID
        tenant_id: Tenant ID
        metadata_store: Metadata store

    Returns:
        File response with the original document
    """
    try:
        meta = metadata_store.get_metadata(document_id, tenant_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        if not meta.original_blob_url:
            raise HTTPException(status_code=404, detail=f"Original document not found for document {document_id}")
        
        # Download the file from blob storage
        blob_client = BlobClientWrapper()
        container_name, blob_path = blob_client._extract_blob_path_from_url(meta.original_blob_url)
        file_bytes = blob_client.download_bytes(container_name, blob_path)
        
        # Determine content type from filename or use default
        content_type = "application/pdf"  # Default
        if meta.original_blob_url:
            if meta.original_blob_url.endswith(".pdf"):
                content_type = "application/pdf"
            elif meta.original_blob_url.endswith((".png", ".jpg", ".jpeg", ".gif")):
                content_type = "image/png" if meta.original_blob_url.endswith(".png") else "image/jpeg"
        
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{document_id}"',
                "Cache-Control": "public, max-age=3600",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving original document: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to serve document: {e!s}")

