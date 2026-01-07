"""Document processing Pydantic models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class DocumentStatus(str, Enum):
    """Document processing status."""

    RECEIVED = "RECEIVED"
    UPLOADED = "UPLOADED"
    CU_PROCESSING = "CU_PROCESSING"
    CU_DONE = "CU_DONE"
    LLM_PROCESSING = "LLM_PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class Cu_Record(BaseModel):
    """Core metadata record for document processing."""

    id: str = Field(..., description="Document ID")
    tenant_id: str = Field(..., alias="tenantId", description="Tenant ID")
    user_id: str = Field(..., alias="userId", description="User ID")
    source_type: str = Field(..., alias="sourceType", description="Source type (e.g., 'pdf', 'image')")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="createdAt", description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="updatedAt", description="Last update timestamp"
    )
    original_blob_url: str | None = Field(
        None, alias="originalBlobUrl", description="URL to original document in blob storage"
    )
    cu_artifact_blob_url: str | None = Field(
        None, alias="cuArtifactBlobUrl", description="URL to CU artifact JSON in blob storage"
    )
    schema_blob_url: str | None = Field(
        None, alias="schemaBlobUrl", description="URL to extracted schema JSON in blob storage"
    )
    image_blob_urls: list[str] | None = Field(
        None, alias="imageBlobUrls", description="URLs to page images in blob storage"
    )
    status: DocumentStatus = Field(default=DocumentStatus.RECEIVED, description="Processing status")
    error: dict[str, Any] | None = Field(None, description="Error details if status is FAILED")
    metrics: dict[str, Any] | None = Field(None, description="Processing metrics")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Point(BaseModel):
    """Point in a polygon."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class EvidenceSpan(BaseModel):
    """Bounding box/polygon evidence for extracted field."""

    page: int = Field(..., description="Page number (1-indexed)")
    polygon: list[Point] = Field(..., description="Polygon coordinates defining the evidence region")
    source_text: str = Field(..., alias="sourceText", description="Source text from the evidence region")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExtractedField(BaseModel):
    """Extracted field with evidence."""

    field_path: str = Field(..., alias="fieldPath", description="Field path (e.g., 'policyholder.name')")
    value: Any = Field(..., description="Extracted value")
    evidence: list[EvidenceSpan] = Field(default_factory=list, description="Evidence spans for this field")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExtractedSchema(BaseModel):
    """Complete extracted schema from document."""

    doc_type: str = Field(..., alias="docType", description="Document type identifier")
    fields: list[ExtractedField] = Field(default_factory=list, description="Extracted fields")
    raw_model_output: dict[str, Any] | None = Field(
        None, alias="rawModelOutput", description="Raw model output for debugging"
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CuPage(BaseModel):
    """Normalized CU page with polygons."""

    page_number: int = Field(..., alias="pageNumber", description="Page number (1-indexed)")
    width: float | None = Field(None, description="Page width in points")
    height: float | None = Field(None, description="Page height in points")
    lines: list[dict[str, Any]] = Field(default_factory=list, description="Lines with polygon data")
    words: list[dict[str, Any]] = Field(default_factory=list, description="Words with polygon data")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CuTable(BaseModel):
    """Normalized CU table with polygons."""

    row_count: int = Field(..., alias="rowCount", description="Number of rows")
    column_count: int = Field(..., alias="columnCount", description="Number of columns")
    cells: list[dict[str, Any]] = Field(default_factory=list, description="Table cells with polygon data")
    bounding_regions: list[dict[str, Any]] = Field(
        default_factory=list, alias="boundingRegions", description="Bounding regions with polygons"
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CuNormalizedDocument(BaseModel):
    """Normalized Content Understanding document output."""

    pages: list[CuPage] = Field(default_factory=list, description="Pages with polygons")
    lines: list[dict[str, Any]] = Field(default_factory=list, description="Lines with polygon data")
    tables: list[CuTable] = Field(default_factory=list, description="Tables with polygon data")
    raw_content: dict[str, Any] | None = Field(None, alias="rawContent", description="Raw CU output for reference")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

