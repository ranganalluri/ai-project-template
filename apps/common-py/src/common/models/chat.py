"""Chat-related Pydantic models."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

    thread_id: str | None = Field(None, alias="threadId", description="Optional thread ID for conversation continuity")
    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    file_ids: list[str] = Field(default_factory=list, alias="fileIds", description="Attached file IDs for this request")
    
    model_config = ConfigDict(populate_by_name=True)  # Allow both threadId and thread_id


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")


# ============================================================================
# Cosmos DB Document Models for agentStore Container
# ============================================================================


class BaseDocument(BaseModel):
    """Base document model with common fields for all agentStore documents."""

    id: str = Field(..., description="Document ID")
    pk: str = Field(..., description="Partition key: tenantId|userId|conversationId")
    type: str = Field(..., description="Document type: conversation, message, run, toolApproval, artifact, runStep")
    tenantId: str = Field(..., description="Tenant ID")
    userId: str = Field(..., description="User ID")
    conversationId: str = Field(..., description="Conversation ID")


class ConversationDocument(BaseDocument):
    """Type A: Conversation document (1 per conversation)."""

    type: str = Field(default="conversation", description="Document type")
    title: str | None = Field(None, description="Conversation title")
    createdAt: str = Field(..., description="Creation timestamp (ISO format)")
    updatedAt: str = Field(..., description="Last update timestamp (ISO format)")
    status: str = Field(default="active", description="Conversation status")
    agent: dict[str, Any] | None = Field(None, description="Agent configuration (agentId, version)")
    system: dict[str, Any] | None = Field(None, description="System configuration (systemPromptVersion, policyFlags)")
    counters: dict[str, int] = Field(
        default_factory=lambda: {"messageSeq": 0, "runSeq": 0},
        description="Sequence counters for messages and runs",
    )


class MessageDocument(BaseDocument):
    """Type B: Message document (many per conversation)."""

    type: str = Field(default="message", description="Document type")
    seq: int = Field(..., description="Message sequence number")
    role: str = Field(..., description="Message role: user, assistant, system, tool")
    createdAt: str = Field(..., description="Creation timestamp (ISO format)")
    runId: str | None = Field(None, description="Associated run ID")
    content: list[dict[str, Any]] = Field(..., description="Message content array")
    metadata: dict[str, Any] | None = Field(None, description="Message metadata (model, tokenUsage, etc.)")


class RunDocument(BaseDocument):
    """Type C: Run document (many per conversation)."""

    type: str = Field(default="run", description="Document type")
    runSeq: int = Field(..., description="Run sequence number")
    status: str = Field(..., description="Run status: running, completed, cancelled, error")
    createdAt: str = Field(..., description="Creation timestamp (ISO format)")
    startedAt: str | None = Field(None, description="Start timestamp (ISO format)")
    completedAt: str | None = Field(None, description="Completion timestamp (ISO format)")
    triggerMessageId: str | None = Field(None, description="ID of message that triggered this run")
    outputMessageId: str | None = Field(None, description="ID of output message from this run")
    llm: dict[str, Any] | None = Field(None, description="LLM configuration and usage (provider, model, tokenUsage)")
    stepsSummary: list[dict[str, Any]] | None = Field(None, description="Summary of run steps")
    error: dict[str, Any] | None = Field(None, description="Error information if run failed")


class ToolApprovalDocument(BaseDocument):
    """Type D: Tool approval document (optional, as needed)."""

    type: str = Field(default="toolApproval", description="Document type")
    runId: str = Field(..., description="Associated run ID")
    toolCallId: str = Field(..., description="Tool call ID")
    toolName: str = Field(..., description="Name of the tool")
    request: dict[str, Any] = Field(..., description="Approval request details (summary, riskLevel, argumentsPreview)")
    status: str = Field(default="pending", description="Approval status: pending, approved, rejected")
    requestedAt: str = Field(..., description="Request timestamp (ISO format)")
    expiresAt: str | None = Field(None, description="Expiration timestamp (ISO format)")
    decision: dict[str, Any] | None = Field(None, description="Decision details if approved/rejected")


class ArtifactDocument(BaseDocument):
    """Type E: Artifact document (files, tool outputs, extracted text pointers)."""

    type: str = Field(default="artifact", description="Document type")
    artifactType: str = Field(..., description="Artifact type: file, tool_output, extracted_text")
    source: str = Field(..., description="Source: user_upload, tool_output, etc.")
    name: str = Field(..., description="Artifact name")
    mimeType: str | None = Field(None, description="MIME type")
    sizeBytes: int | None = Field(None, description="Size in bytes")
    createdAt: str = Field(..., description="Creation timestamp (ISO format)")
    runId: str | None = Field(None, description="Associated run ID")
    storage: dict[str, Any] = Field(..., description="Storage information (provider, container, blobPath)")
    hash: dict[str, str] | None = Field(None, description="Hash information (alg, value)")


class RunStepDocument(BaseDocument):
    """Type F: Run step document (optional, for deep tracing)."""

    type: str = Field(default="runStep", description="Document type")
    runId: str = Field(..., description="Associated run ID")
    step: int = Field(..., description="Step number")
    kind: str = Field(..., description="Step kind: prep, tool, llm, etc.")
    toolCallId: str | None = Field(None, description="Tool call ID if applicable")
    toolName: str | None = Field(None, description="Tool name if applicable")
    status: str = Field(..., description="Step status: success, error, pending")
    startedAt: str = Field(..., description="Start timestamp (ISO format)")
    endedAt: str | None = Field(None, description="End timestamp (ISO format)")
    outputsArtifactId: str | None = Field(None, description="Artifact ID for step outputs")
