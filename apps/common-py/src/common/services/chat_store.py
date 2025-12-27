"""Chat store with Cosmos DB implementation."""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from common.models.chat import ChatMessage, FileUploadResponse, ToolCall

logger = logging.getLogger(__name__)


class ChatStore(ABC):
    """Abstract interface for chat store."""

    @abstractmethod
    def create_run(self, thread_id: str | None = None) -> str:
        """Create a new run."""
        pass

    @abstractmethod
    def add_message(self, run_id: str, message: ChatMessage) -> None:
        """Add a message to a run."""
        pass

    @abstractmethod
    def get_messages(self, run_id: str) -> list[ChatMessage]:
        """Get all messages for a run."""
        pass

    @abstractmethod
    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall) -> None:
        """Add a pending tool call."""
        pass

    @abstractmethod
    def approve_tool_call(self, run_id: str, tool_call_id: str, approved: bool) -> None:
        """Approve or reject a tool call."""
        pass

    @abstractmethod
    def get_tool_call_approval(self, run_id: str, tool_call_id: str) -> bool | None:
        """Get tool call approval status."""
        pass

    @abstractmethod
    def get_pending_tool_call(self, run_id: str, tool_call_id: str) -> ToolCall | None:
        """Get a pending tool call."""
        pass

    @abstractmethod
    def cancel_run(self, run_id: str) -> None:
        """Cancel a run."""
        pass

    @abstractmethod
    def is_cancelled(self, run_id: str) -> bool:
        """Check if a run is cancelled."""
        pass

    @abstractmethod
    def complete_run(self, run_id: str) -> None:
        """Mark a run as completed."""
        pass

    @abstractmethod
    def error_run(self, run_id: str) -> None:
        """Mark a run as error."""
        pass

    @abstractmethod
    def store_file(self, file_id: str, file_data: FileUploadResponse) -> None:
        """Store file metadata."""
        pass

    @abstractmethod
    def get_file(self, file_id: str) -> FileUploadResponse | None:
        """Get file metadata."""
        pass


class CosmosChatStore(ChatStore):
    """Cosmos DB implementation of ChatStore."""

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_key: str | None = None,
        database_name: str = "agentic",
        runs_container_name: str = "runs",
        files_container_name: str = "files",
        use_managed_identity: bool = False,
    ) -> None:
        """Initialize Cosmos DB chat store.

        Args:
            cosmos_endpoint: Cosmos DB endpoint URL
            cosmos_key: Cosmos DB key (if not using managed identity)
            database_name: Database name
            runs_container_name: Container name for runs
            files_container_name: Container name for file metadata
            use_managed_identity: Use managed identity for authentication
        """
        if use_managed_identity:
            credential = DefaultAzureCredential()
            self.client = CosmosClient(cosmos_endpoint, credential)
        else:
            if not cosmos_key:
                raise ValueError("cosmos_key is required when not using managed identity")
            self.client = CosmosClient(cosmos_endpoint, cosmos_key)

        self.database = self.client.get_database_client(database_name)
        self.runs_container = self.database.get_container_client(runs_container_name)
        self.files_container = self.database.get_container_client(files_container_name)

    def create_run(self, thread_id: str | None = None) -> str:
        """Create a new run."""
        run_id = str(uuid.uuid4())
        # Use thread_id as partition key if available, otherwise use run_id
        partition_key = thread_id or run_id

        run_doc = {
            "id": run_id,
            "run_id": run_id,
            "thread_id": thread_id,
            "status": "running",
            "created_at": datetime.now(UTC).isoformat(),
            "messages": [],
            "pending_tool_calls": {},
            "tool_call_approvals": {},
            "cancelled": False,
        }

        self.runs_container.create_item(
            body=run_doc,
            enable_automatic_id_generation=False,
            partition_key=partition_key,
        )
        logger.info("Created run %s", run_id)
        return run_id

    def _get_run_doc(self, run_id: str) -> dict[str, Any] | None:
        """Get run document from Cosmos DB."""
        try:
            # Try to get by run_id (partition key might be thread_id or run_id)
            query = "SELECT * FROM c WHERE c.run_id = @run_id"
            items = list(
                self.runs_container.query_items(
                    query=query,
                    parameters=[{"name": "@run_id", "value": run_id}],
                    enable_cross_partition_query=True,
                )
            )
            if items:
                return items[0]
            return None
        except CosmosResourceNotFoundError:
            return None

    def _update_run_doc(self, run_id: str, updates: dict[str, Any]) -> None:
        """Update run document in Cosmos DB."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            raise ValueError(f"Run {run_id} not found")

        run_doc.update(updates)
        partition_key = run_doc.get("thread_id") or run_doc.get("run_id")
        self.runs_container.replace_item(
            item=run_doc["id"],
            body=run_doc,
            partition_key=partition_key,
        )

    def add_message(self, run_id: str, message: ChatMessage) -> None:
        """Add a message to a run."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            raise ValueError(f"Run {run_id} not found")

        if "messages" not in run_doc:
            run_doc["messages"] = []

        run_doc["messages"].append(message.model_dump())
        self._update_run_doc(run_id, {"messages": run_doc["messages"]})

    def get_messages(self, run_id: str) -> list[ChatMessage]:
        """Get all messages for a run."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            return []

        messages_data = run_doc.get("messages", [])
        return [ChatMessage(**msg) for msg in messages_data]

    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall) -> None:
        """Add a pending tool call."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            raise ValueError(f"Run {run_id} not found")

        if "pending_tool_calls" not in run_doc:
            run_doc["pending_tool_calls"] = {}
        if "tool_call_approvals" not in run_doc:
            run_doc["tool_call_approvals"] = {}

        run_doc["pending_tool_calls"][tool_call.id] = tool_call.model_dump()
        run_doc["tool_call_approvals"][tool_call.id] = None

        self._update_run_doc(
            run_id,
            {
                "pending_tool_calls": run_doc["pending_tool_calls"],
                "tool_call_approvals": run_doc["tool_call_approvals"],
            },
        )

    def approve_tool_call(self, run_id: str, tool_call_id: str, approved: bool) -> None:
        """Approve or reject a tool call."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            raise ValueError(f"Run {run_id} not found")

        if "tool_call_approvals" not in run_doc:
            run_doc["tool_call_approvals"] = {}

        run_doc["tool_call_approvals"][tool_call_id] = approved
        self._update_run_doc(run_id, {"tool_call_approvals": run_doc["tool_call_approvals"]})
        logger.info(
            "Tool call %s in run %s %s",
            tool_call_id,
            run_id,
            "approved" if approved else "rejected",
        )

    def get_tool_call_approval(self, run_id: str, tool_call_id: str) -> bool | None:
        """Get tool call approval status."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            return None

        approvals = run_doc.get("tool_call_approvals", {})
        return approvals.get(tool_call_id)

    def get_pending_tool_call(self, run_id: str, tool_call_id: str) -> ToolCall | None:
        """Get a pending tool call."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            return None

        tool_calls = run_doc.get("pending_tool_calls", {})
        tool_call_data = tool_calls.get(tool_call_id)
        if tool_call_data:
            return ToolCall(**tool_call_data)
        return None

    def cancel_run(self, run_id: str) -> None:
        """Cancel a run."""
        self._update_run_doc(run_id, {"status": "cancelled", "cancelled": True})
        logger.info("Cancelled run %s", run_id)

    def is_cancelled(self, run_id: str) -> bool:
        """Check if a run is cancelled."""
        run_doc = self._get_run_doc(run_id)
        if not run_doc:
            return False
        return run_doc.get("cancelled", False)

    def complete_run(self, run_id: str) -> None:
        """Mark a run as completed."""
        self._update_run_doc(run_id, {"status": "completed"})

    def error_run(self, run_id: str) -> None:
        """Mark a run as error."""
        self._update_run_doc(run_id, {"status": "error"})

    def store_file(self, file_id: str, file_data: FileUploadResponse) -> None:
        """Store file metadata."""
        file_doc = {
            "id": file_id,
            "file_id": file_id,
            **file_data.model_dump(),
        }
        try:
            self.files_container.upsert_item(body=file_doc)
        except Exception as e:
            logger.error("Error storing file metadata: %s", e)
            raise

    def get_file(self, file_id: str) -> FileUploadResponse | None:
        """Get file metadata."""
        try:
            file_doc = self.files_container.read_item(item=file_id, partition_key=file_id)
            return FileUploadResponse(
                file_id=file_doc["file_id"],
                filename=file_doc["filename"],
                content_type=file_doc["content_type"],
                size=file_doc["size"],
            )
        except CosmosResourceNotFoundError:
            return None
