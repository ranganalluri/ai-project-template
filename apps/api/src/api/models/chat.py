"""Chat-related Pydantic models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    file_ids: list[str] = Field(default_factory=list, description="Attached file IDs")


class ChatRequest(BaseModel):
    """Request model for chat stream."""

    thread_id: str | None = Field(None, description="Optional thread ID for conversation continuity")
    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    file_ids: list[str] = Field(default_factory=list, description="Attached file IDs for this request")


class ToolCall(BaseModel):
    """Tool call model."""

    id: str = Field(..., description="Tool call ID")
    name: str = Field(..., description="Tool name")
    arguments_json: str = Field(..., description="Tool arguments as JSON string")


class ToolApprovalRequest(BaseModel):
    """Request model for tool approval."""

    approved: bool = Field(..., description="Whether the tool call is approved")


class RunStatus(BaseModel):
    """Run status model."""

    run_id: str = Field(..., description="Run ID")
    status: str = Field(..., description="Run status: running, completed, cancelled, error")
    thread_id: str | None = Field(None, description="Thread ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

