"""Chat routes for streaming conversations."""

import logging
import uuid

from api.config import Settings, get_settings
from api.services import get_chat_store, get_file_storage
from api.services.chat_service import ChatService
from api.services.foundry_client import FoundryClient
from common.models.chat import ChatRequest, FileUploadResponse, ToolApprovalRequest
from common.services.chat_store import ChatStore
from common.services.file_storage import FileStorage
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


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
    chat_store: ChatStore = Depends(get_chat_store),
) -> ChatService:
    """Get chat service dependency.

    Args:
        foundry_client: Foundry client
        settings: Application settings
        chat_store: Chat store

    Returns:
        ChatService instance
    """
    return ChatService(foundry_client, settings, chat_store)


@router.post("/files", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    file_storage: FileStorage = Depends(get_file_storage),
    chat_store: ChatStore = Depends(get_chat_store),
) -> FileUploadResponse:
    """Upload a file.

    Args:
        file: Uploaded file
        file_storage: Blob Storage file service
        chat_store: Chat store for metadata

    Returns:
        File upload response with file ID
    """
    try:
        # Generate file ID
        file_id = str(uuid.uuid4())

        # Read file content
        content = await file.read()

        # Store metadata
        file_data = FileUploadResponse(
            file_id=file_id,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
        )

        # Upload to Blob Storage
        file_storage.upload_file(file_id, content, file_data)

        # Store metadata in Cosmos DB
        chat_store.store_file(file_id, file_data)

        logger.info("Uploaded file %s: %s", file_id, file.filename)
        return file_data

    except Exception as e:
        logger.error("Error uploading file: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e!s}")


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    chat_store: ChatStore = Depends(get_chat_store),
) -> StreamingResponse:
    """Stream chat completion with SSE.

    Args:
        request: Chat request
        chat_service: Chat service
        chat_store: Chat store

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
        logger.error("Error in stream_chat: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat streaming failed: {e!s}")


@router.post("/runs/{run_id}/stop")
async def stop_run(
    run_id: str,
    chat_store: ChatStore = Depends(get_chat_store),
) -> dict[str, str]:
    """Stop/cancel a running chat.

    Args:
        run_id: Run ID
        chat_store: Chat store

    Returns:
        Success message
    """
    chat_store.cancel_run(run_id)
    logger.info("Stopped run %s", run_id)
    return {"status": "cancelled", "runId": run_id}


@router.post("/runs/{run_id}/toolcalls/{tool_call_id}")
async def approve_tool_call(
    run_id: str,
    tool_call_id: str,
    request: ToolApprovalRequest,
    chat_store: ChatStore = Depends(get_chat_store),
) -> dict[str, str]:
    """Approve or reject a tool call.

    Args:
        run_id: Run ID
        tool_call_id: Tool call ID
        request: Approval request
        chat_store: Chat store

    Returns:
        Success message
    """
    chat_store.approve_tool_call(run_id, tool_call_id, request.approved)
    logger.info(
        "Tool call %s in run %s %s",
        tool_call_id,
        run_id,
        "approved" if request.approved else "rejected",
    )
    return {
        "status": "approved" if request.approved else "rejected",
        "runId": run_id,
        "toolCallId": tool_call_id,
    }
