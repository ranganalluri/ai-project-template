"""Document processing Pydantic models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Document processing status."""

    RECEIVED = "RECEIVED"
    UPLOADED = "UPLOADED"
    CU_PROCESSING = "CU_PROCESSING"
    CU_DONE = "CU_DONE"
    LLM_PROCESSING = "LLM_PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class DocumentMetadata(BaseModel):
    """Core metadata record for document processing."""

    id: str = Field(..., description="Document ID")
    tenantId: str = Field(..., description="Tenant ID")
    userId: str = Field(..., description="User ID")
    sourceType: str = Field(..., description="Source type (e.g., 'pdf', 'image')")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")
    originalBlobUrl: str | None = Field(None, description="URL to original document in blob storage")
    cuArtifactBlobUrl: str | None = Field(None, description="URL to CU artifact JSON in blob storage")
    schemaBlobUrl: str | None = Field(None, description="URL to extracted schema JSON in blob storage")
    status: DocumentStatus = Field(default=DocumentStatus.RECEIVED, description="Processing status")
    error: dict[str, Any] | None = Field(None, description="Error details if status is FAILED")
    metrics: dict[str, Any] | None = Field(None, description="Processing metrics")

    model_config = {"extra": "forbid"}


class Point(BaseModel):
    """Point in a polygon."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class EvidenceSpan(BaseModel):
    """Bounding box/polygon evidence for extracted field."""

    page: int = Field(..., description="Page number (1-indexed)")
    polygon: list[Point] = Field(..., description="Polygon coordinates defining the evidence region")
    sourceText: str = Field(..., description="Source text from the evidence region")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")


class ExtractedField(BaseModel):
    """Extracted field with evidence."""

    fieldPath: str = Field(..., description="Field path (e.g., 'policyholder.name')")
    value: Any = Field(..., description="Extracted value")
    evidence: list[EvidenceSpan] = Field(default_factory=list, description="Evidence spans for this field")


class ExtractedSchema(BaseModel):
    """Complete extracted schema from document."""

    docType: str = Field(..., description="Document type identifier")
    fields: list[ExtractedField] = Field(default_factory=list, description="Extracted fields")
    rawModelOutput: dict[str, Any] | None = Field(None, description="Raw model output for debugging")


class CuPage(BaseModel):
    """Normalized CU page with polygons."""

    pageNumber: int = Field(..., description="Page number (1-indexed)")
    width: float | None = Field(None, description="Page width in points")
    height: float | None = Field(None, description="Page height in points")
    lines: list[dict[str, Any]] = Field(default_factory=list, description="Lines with polygon data")
    words: list[dict[str, Any]] = Field(default_factory=list, description="Words with polygon data")


class CuTable(BaseModel):
    """Normalized CU table with polygons."""

    rowCount: int = Field(..., description="Number of rows")
    columnCount: int = Field(..., description="Number of columns")
    cells: list[dict[str, Any]] = Field(default_factory=list, description="Table cells with polygon data")
    boundingRegions: list[dict[str, Any]] = Field(default_factory=list, description="Bounding regions with polygons")


class CuNormalizedDocument(BaseModel):
    """Normalized Content Understanding document output."""

    pages: list[CuPage] = Field(default_factory=list, description="Pages with polygons")
    lines: list[dict[str, Any]] = Field(default_factory=list, description="Lines with polygon data")
    tables: list[CuTable] = Field(default_factory=list, description="Tables with polygon data")
    rawContent: dict[str, Any] | None = Field(None, description="Raw CU output for reference")

