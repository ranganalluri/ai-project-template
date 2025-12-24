"""Chat routes for streaming conversations."""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from fastapi.responses import StreamingResponse

from api.config import Settings, get_settings
from api.models.chat import ChatMessage, ChatRequest, FileUploadResponse, ToolApprovalRequest
from api.services.chat_service import ChatService
from api.services.chat_store import chat_store
from api.services.foundry_client import FoundryClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

# Ensure uploads directory exists
UPLOADS_DIR = Path("./data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_foundry_client(settings: Settings = Depends(get_settings)) -> FoundryClient:
    """Get Foundry client dependency.

    Args:
        settings: Application settings

    Returns:
        FoundryClient instance
    """
    return FoundryClient(settings)


def get_chat_service(
    foundry_client: FoundryClient = Depends(get_foundry_client),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    """Get chat service dependency.

    Args:
        foundry_client: Foundry client
        settings: Application settings

    Returns:
        ChatService instance
    """
    return ChatService(foundry_client, settings)


@router.post("/files", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
) -> FileUploadResponse:
    """Upload a file.

    Args:
        file: Uploaded file

    Returns:
        File upload response with file ID
    """
    try:
        # Generate file ID
        file_id = str(uuid.uuid4())

        # Save file
        file_path = UPLOADS_DIR / file_id
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Store metadata
        file_data = FileUploadResponse(
            file_id=file_id,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
        )
        chat_store.store_file(file_id, file_data)

        logger.info(f"Uploaded file {file_id}: {file.filename}")
        return file_data

    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream chat completion with SSE.

    Args:
        request: Chat request
        chat_service: Chat service

    Returns:
        StreamingResponse with SSE events
    """
    try:
        # Create run
        run_id = chat_store.create_run(request.thread_id)

        # Store initial messages
        for msg in request.messages:
            chat_store.add_message(run_id, msg)

        # Start streaming
        async def event_generator():
            async for event in chat_service.stream_chat(run_id, request.messages, request.file_ids):
                yield event

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Error in stream_chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat streaming failed: {str(e)}")


@router.post("/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict[str, str]:
    """Stop/cancel a running chat.

    Args:
        run_id: Run ID

    Returns:
        Success message
    """
    chat_store.cancel_run(run_id)
    logger.info(f"Stopped run {run_id}")
    return {"status": "cancelled", "runId": run_id}


@router.post("/runs/{run_id}/toolcalls/{tool_call_id}")
async def approve_tool_call(
    run_id: str,
    tool_call_id: str,
    request: ToolApprovalRequest,
) -> dict[str, str]:
    """Approve or reject a tool call.

    Args:
        run_id: Run ID
        tool_call_id: Tool call ID
        request: Approval request

    Returns:
        Success message
    """
    chat_store.approve_tool_call(run_id, tool_call_id, request.approved)
    logger.info(f"Tool call {tool_call_id} in run {run_id} {'approved' if request.approved else 'rejected'}")
    return {
        "status": "approved" if request.approved else "rejected",
        "runId": run_id,
        "toolCallId": tool_call_id,
    }

