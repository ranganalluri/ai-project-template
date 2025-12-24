"""In-memory store for chat data."""

import logging
import uuid
from datetime import datetime
from typing import Any

from api.models.chat import ChatMessage, FileUploadResponse, RunStatus, ToolCall

logger = logging.getLogger(__name__)


class ChatStore:
    """In-memory store for chat sessions, runs, messages, and files."""

    def __init__(self) -> None:
        """Initialize the store."""
        self.runs: dict[str, RunStatus] = {}
        self.messages: dict[str, list[ChatMessage]] = {}  # run_id -> messages
        self.pending_tool_calls: dict[str, dict[str, ToolCall]] = {}  # run_id -> {tool_call_id -> ToolCall}
        self.tool_call_approvals: dict[str, dict[str, bool | None]] = {}  # run_id -> {tool_call_id -> approved}
        self.files: dict[str, FileUploadResponse] = {}  # file_id -> file metadata
        self.run_cancelled: dict[str, bool] = {}  # run_id -> cancelled flag

    def create_run(self, thread_id: str | None = None) -> str:
        """Create a new run.

        Args:
            thread_id: Optional thread ID

        Returns:
            Run ID
        """
        run_id = str(uuid.uuid4())
        self.runs[run_id] = RunStatus(
            run_id=run_id,
            status="running",
            thread_id=thread_id,
            created_at=datetime.utcnow(),
        )
        self.messages[run_id] = []
        self.pending_tool_calls[run_id] = {}
        self.tool_call_approvals[run_id] = {}
        self.run_cancelled[run_id] = False
        logger.info(f"Created run {run_id}")
        return run_id

    def add_message(self, run_id: str, message: ChatMessage) -> None:
        """Add a message to a run.

        Args:
            run_id: Run ID
            message: Message to add
        """
        if run_id not in self.messages:
            self.messages[run_id] = []
        self.messages[run_id].append(message)

    def get_messages(self, run_id: str) -> list[ChatMessage]:
        """Get all messages for a run.

        Args:
            run_id: Run ID

        Returns:
            List of messages
        """
        return self.messages.get(run_id, [])

    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall) -> None:
        """Add a pending tool call.

        Args:
            run_id: Run ID
            tool_call: Tool call to add
        """
        if run_id not in self.pending_tool_calls:
            self.pending_tool_calls[run_id] = {}
        self.pending_tool_calls[run_id][tool_call.id] = tool_call
        if run_id not in self.tool_call_approvals:
            self.tool_call_approvals[run_id] = {}
        self.tool_call_approvals[run_id][tool_call.id] = None

    def approve_tool_call(self, run_id: str, tool_call_id: str, approved: bool) -> None:
        """Approve or reject a tool call.

        Args:
            run_id: Run ID
            tool_call_id: Tool call ID
            approved: Whether the tool call is approved
        """
        if run_id not in self.tool_call_approvals:
            self.tool_call_approvals[run_id] = {}
        self.tool_call_approvals[run_id][tool_call_id] = approved
        logger.info(f"Tool call {tool_call_id} in run {run_id} {'approved' if approved else 'rejected'}")

    def get_tool_call_approval(self, run_id: str, tool_call_id: str) -> bool | None:
        """Get tool call approval status.

        Args:
            run_id: Run ID
            tool_call_id: Tool call ID

        Returns:
            Approval status (True/False) or None if pending
        """
        return self.tool_call_approvals.get(run_id, {}).get(tool_call_id)

    def get_pending_tool_call(self, run_id: str, tool_call_id: str) -> ToolCall | None:
        """Get a pending tool call.

        Args:
            run_id: Run ID
            tool_call_id: Tool call ID

        Returns:
            Tool call or None
        """
        return self.pending_tool_calls.get(run_id, {}).get(tool_call_id)

    def cancel_run(self, run_id: str) -> None:
        """Cancel a run.

        Args:
            run_id: Run ID
        """
        self.run_cancelled[run_id] = True
        if run_id in self.runs:
            self.runs[run_id].status = "cancelled"
        logger.info(f"Cancelled run {run_id}")

    def is_cancelled(self, run_id: str) -> bool:
        """Check if a run is cancelled.

        Args:
            run_id: Run ID

        Returns:
            True if cancelled
        """
        return self.run_cancelled.get(run_id, False)

    def complete_run(self, run_id: str) -> None:
        """Mark a run as completed.

        Args:
            run_id: Run ID
        """
        if run_id in self.runs:
            self.runs[run_id].status = "completed"

    def error_run(self, run_id: str) -> None:
        """Mark a run as error.

        Args:
            run_id: Run ID
        """
        if run_id in self.runs:
            self.runs[run_id].status = "error"

    def store_file(self, file_id: str, file_data: FileUploadResponse) -> None:
        """Store file metadata.

        Args:
            file_id: File ID
            file_data: File metadata
        """
        self.files[file_id] = file_data

    def get_file(self, file_id: str) -> FileUploadResponse | None:
        """Get file metadata.

        Args:
            file_id: File ID

        Returns:
            File metadata or None
        """
        return self.files.get(file_id)


# Global store instance
chat_store = ChatStore()

