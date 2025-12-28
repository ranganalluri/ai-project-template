"""Chat store with Cosmos DB implementation."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential


from common.models.chat import (
    ArtifactDocument,
    ChatMessage,
    ConversationDocument,
    FileUploadResponse,
    MessageDocument,
    RunDocument,
    ToolApprovalDocument,
    ToolCall,
)

logger = logging.getLogger(__name__)


class ChatStore(ABC):
    """Abstract interface for chat store."""

    @abstractmethod
    def create_run(self, thread_id: str | None = None) -> str:
        """Create a new run."""

    @abstractmethod
    def add_message(self, run_id: str, message: ChatMessage) -> None:
        """Add a message to a run."""

    @abstractmethod
    def get_messages(self, run_id: str) -> list[ChatMessage]:
        """Get all messages for a run."""

    @abstractmethod
    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall) -> None:
        """Add a pending tool call."""

    @abstractmethod
    def approve_tool_call(self, run_id: str, tool_call_id: str, approved: bool) -> None:
        """Approve or reject a tool call."""

    @abstractmethod
    def get_tool_call_approval(self, run_id: str, tool_call_id: str) -> bool | None:
        """Get tool call approval status."""

    @abstractmethod
    def get_pending_tool_call(self, run_id: str, tool_call_id: str) -> ToolCall | None:
        """Get a pending tool call."""

    @abstractmethod
    def cancel_run(self, run_id: str) -> None:
        """Cancel a run."""

    @abstractmethod
    def is_cancelled(self, run_id: str) -> bool:
        """Check if a run is cancelled."""

    @abstractmethod
    def complete_run(self, run_id: str) -> None:
        """Mark a run as completed."""

    @abstractmethod
    def error_run(self, run_id: str) -> None:
        """Mark a run as error."""

    @abstractmethod
    def store_file(self, file_id: str, file_data: FileUploadResponse) -> None:
        """Store file metadata."""

    @abstractmethod
    def get_file(self, file_id: str) -> FileUploadResponse | None:
        """Get file metadata."""


class CosmosChatStore(ChatStore):
    """Cosmos DB implementation of ChatStore using single agentStore container."""

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_key: str | None = None,
        database_name: str = "agenticdb",
        agent_store_container_name: str = "agentStore",
        default_tenant_id: str = "t1",
        use_managed_identity: bool = False,
        # Legacy parameters for backward compatibility
        runs_container_name: str | None = None,
        files_container_name: str | None = None,
    ) -> None:
        """Initialize Cosmos DB chat store.

        Args:
            cosmos_endpoint: Cosmos DB endpoint URL
            cosmos_key: Cosmos DB key (if not using managed identity)
            database_name: Database name (default: agenticdb)
            agent_store_container_name: Container name for agentStore (default: agentStore)
            default_tenant_id: Default tenant ID to use (default: t1)
            use_managed_identity: Use managed identity for authentication
            runs_container_name: Legacy parameter (ignored)
            files_container_name: Legacy parameter (ignored)
        """
        
        if use_managed_identity:
            credential = DefaultAzureCredential()
            self.client = CosmosClient(cosmos_endpoint, credential)
        else:
            if not cosmos_key:
                raise ValueError("cosmos_key is required when not using managed identity")
            self.client = CosmosClient(cosmos_endpoint, cosmos_key)

        self.database = self.client.get_database_client(database_name)
        self.agent_store_container = self.database.get_container_client(agent_store_container_name)
        self.default_tenant_id = default_tenant_id

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _build_partition_key(self, tenant_id: str, user_id: str, conversation_id: str) -> str:
        """Build partition key in format: tenantId|userId|conversationId."""
        return f"{tenant_id}|{user_id}|{conversation_id}"

    def _generate_message_id(self, seq: int) -> str:
        """Generate message ID with zero-padded format: msg_000012."""
        return f"msg_{seq:06d}"

    def _generate_run_id(self, seq: int) -> str:
        """Generate run ID with zero-padded format: run_000004."""
        return f"run_{seq:06d}"

    def _get_conversation_doc(
        self, tenant_id: str, user_id: str, conversation_id: str
    ) -> dict[str, Any] | None:
        """Get conversation document by ID."""
        try:
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            doc = self.agent_store_container.read_item(
                item=conversation_id, partition_key=pk
            )
            return doc
        except CosmosResourceNotFoundError:
            return None

    def _create_or_update_conversation(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        title: str | None = None,
        agent: dict[str, Any] | None = None,
        system: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update conversation document."""
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        now = datetime.now(UTC).isoformat()

        conv_doc = self._get_conversation_doc(tenant_id, user_id, conversation_id)
        if conv_doc:
            # Update existing
            if title:
                conv_doc["title"] = title
            if agent:
                conv_doc["agent"] = agent
            if system:
                conv_doc["system"] = system
            conv_doc["updatedAt"] = now
            self.agent_store_container.upsert_item(conv_doc)
            return conv_doc

        # Create new
        conv_doc = {
            "id": conversation_id,
            "pk": pk,
            "type": "conversation",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "title": title,
            "createdAt": now,
            "updatedAt": now,
            "status": "active",
            "agent": agent,
            "system": system,
            "counters": {"messageSeq": 0, "runSeq": 0},
        }
        self.agent_store_container.create_item(conv_doc)
        return conv_doc

    def _increment_counter(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        counter_name: str,
        max_retries: int = 5,
    ) -> int:
        """Increment counter in conversation document using TransactionalBatch.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            conversation_id: Conversation ID
            counter_name: Counter name ('messageSeq' or 'runSeq')
            max_retries: Maximum number of retries on conflict

        Returns:
            New counter value after increment
        """
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        for attempt in range(max_retries):
            try:
                # Read conversation document
                conv_doc = self._get_conversation_doc(tenant_id, user_id, conversation_id)
                if not conv_doc:
                    # Create conversation if it doesn't exist
                    conv_doc = self._create_or_update_conversation(
                        tenant_id, user_id, conversation_id
                    )

                current_value = conv_doc.get("counters", {}).get(counter_name, 0)
                new_value = current_value + 1

                # Update with ETag-based optimistic concurrency
                updated_doc = {
                    **conv_doc,
                    "counters": {
                        **conv_doc.get("counters", {}),
                        counter_name: new_value,
                    },
                    "updatedAt": datetime.now(UTC).isoformat(),
                }

                # Remove _etag from body (it's metadata, not part of the document)
                if "_etag" in updated_doc:
                    etag = updated_doc.pop("_etag")
                else:
                    etag = conv_doc.get("_etag")

                # Ensure partition key is in the document body
                updated_doc["pk"] = pk

                # Use replace_item with if_match for optimistic concurrency
                # Note: partition_key is not passed separately to avoid SDK bug where it's
                # incorrectly passed to Session.request(). The SDK extracts it from the document's 'pk' field.
                self.agent_store_container.replace_item(
                    item=conversation_id,
                    body=updated_doc,
                    if_match=etag,
                )

                return new_value

            except CosmosAccessConditionFailedError:
                # ETag conflict - retry
                if attempt < max_retries - 1:
                    # Exponential backoff
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                raise
            except Exception as e:
                logger.error("Error incrementing counter: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                raise

        raise Exception(f"Failed to increment counter after {max_retries} attempts")

    def _get_run_doc(
        self, tenant_id: str, user_id: str, conversation_id: str, run_id: str
    ) -> dict[str, Any] | None:
        """Get run document by ID."""
        try:
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            if doc.get("type") == "run":
                return doc
            return None
        except CosmosResourceNotFoundError:
            return None

    def _query_by_type(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        doc_type: str,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query documents by type within a partition."""
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        query = f"SELECT * FROM c WHERE c.pk = @pk AND c.type = @type"

        if order_by:
            query += f" ORDER BY c.{order_by} DESC"

        parameters = [
            {"name": "@pk", "value": pk},
            {"name": "@type", "value": doc_type},
        ]

        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=pk,
            )
        )

        if offset > 0:
            items = items[offset:]
        if limit:
            items = items[:limit]

        return items

    def create_run(self, thread_id: str | None = None, user_id: str = "default", tenant_id: str | None = None) -> str:
        """Create a new run.

        Args:
            thread_id: Thread/conversation ID (used as conversation_id)
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            Run ID
        """
        import uuid

        tenant_id = tenant_id or self.default_tenant_id
        if thread_id:
            # Ensure conversation_id starts with "conv_"
            if not thread_id.startswith("conv_"):
                conversation_id = f"conv_{thread_id}"
            else:
                conversation_id = thread_id
        else:
            conversation_id = f"conv_{uuid.uuid4().hex[:16]}"

        # Ensure conversation exists
        self._create_or_update_conversation(tenant_id, user_id, conversation_id)

        # Increment run counter
        run_seq = self._increment_counter(tenant_id, user_id, conversation_id, "runSeq")
        run_id = self._generate_run_id(run_seq)
        now = datetime.now(UTC).isoformat()

        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        run_doc = {
            "id": run_id,
            "pk": pk,
            "type": "run",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "runSeq": run_seq,
            "status": "running",
            "createdAt": now,
            "startedAt": now,
            "completedAt": None,
            "triggerMessageId": None,
            "outputMessageId": None,
            "llm": None,
            "stepsSummary": None,
            "error": None,
        }

        self.agent_store_container.create_item(run_doc)
        logger.info("Created run %s for conversation %s", run_id, conversation_id)
        return run_id

    def add_message(self, run_id: str, message: ChatMessage, user_id: str = "default", tenant_id: str | None = None) -> None:
        """Add a message to a run.

        Args:
            run_id: Run ID
            message: Message to add
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)
        """
        tenant_id = tenant_id or self.default_tenant_id

        # Get run to find conversation_id
        # Since we don't know the partition key, we need to query
        # For now, we'll need to store conversation_id in run or query by run_id
        # Let's query by run_id across partitions (inefficient but works)
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise ValueError(f"Run {run_id} not found")

        run_doc = items[0]
        conversation_id = run_doc["conversationId"]
        user_id = run_doc["userId"]
        tenant_id = run_doc["tenantId"]

        # Increment message counter
        msg_seq = self._increment_counter(tenant_id, user_id, conversation_id, "messageSeq")
        msg_id = self._generate_message_id(msg_seq)
        now = datetime.now(UTC).isoformat()

        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Convert ChatMessage to MessageDocument format
        content = [{"type": "text", "text": message.content}]

        message_doc = {
            "id": msg_id,
            "pk": pk,
            "type": "message",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "seq": msg_seq,
            "role": message.role,
            "createdAt": now,
            "runId": run_id,
            "content": content,
            "metadata": None,
        }

        self.agent_store_container.create_item(message_doc)
        logger.debug("Added message %s to run %s", msg_id, run_id)

    def get_conversation_id_from_run(self, run_id: str) -> str | None:
        """Get conversation ID from a run ID.

        Args:
            run_id: Run ID

        Returns:
            Conversation ID or None if run not found
        """
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return None

        return items[0].get("conversationId")

    def get_messages(self, run_id: str) -> list[ChatMessage]:
        """Get all messages for a run.

        Args:
            run_id: Run ID

        Returns:
            List of ChatMessage objects
        """
        # Get run to find conversation_id
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return []

        run_doc = items[0]
        conversation_id = run_doc["conversationId"]
        user_id = run_doc["userId"]
        tenant_id = run_doc["tenantId"]

        # Query messages for this conversation
        messages = self._query_by_type(tenant_id, user_id, conversation_id, "message", "seq")

        # Convert to ChatMessage format
        result = []
        for msg_doc in messages:
            # Extract text content from content array
            content_text = ""
            if msg_doc.get("content"):
                for content_item in msg_doc["content"]:
                    if content_item.get("type") == "text":
                        content_text += content_item.get("text", "")

            result.append(
                ChatMessage(
                    role=msg_doc["role"],
                    content=content_text,
                    file_ids=[],  # TODO: Extract from message if stored
                )
            )

        return result

    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall) -> None:
        """Add a pending tool call."""
        # Get run to find partition info
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise ValueError(f"Run {run_id} not found")

        run_doc = items[0]
        conversation_id = run_doc["conversationId"]
        user_id = run_doc["userId"]
        tenant_id = run_doc["tenantId"]
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Create tool approval document
        approval_id = f"appr_{run_id}_{tool_call.id}"
        now = datetime.now(UTC).isoformat()

        approval_doc = {
            "id": approval_id,
            "pk": pk,
            "type": "toolApproval",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "runId": run_id,
            "toolCallId": tool_call.id,
            "toolName": tool_call.name,
            "request": {
                "summary": f"Tool call: {tool_call.name}",
                "riskLevel": "medium",
                "argumentsPreview": tool_call.arguments_json[:200] if len(tool_call.arguments_json) > 200 else tool_call.arguments_json,
            },
            "status": "pending",
            "requestedAt": now,
            "expiresAt": None,
            "decision": None,
        }

        self.agent_store_container.create_item(approval_doc)
        logger.info("Added pending tool call %s for run %s", tool_call.id, run_id)

    def approve_tool_call(self, run_id: str, tool_call_id: str, approved: bool) -> None:
        """Approve or reject a tool call."""
        # Get run to find partition info
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise ValueError(f"Run {run_id} not found")

        run_doc = items[0]
        conversation_id = run_doc["conversationId"]
        user_id = run_doc["userId"]
        tenant_id = run_doc["tenantId"]
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Find approval document
        approval_id = f"appr_{run_id}_{tool_call_id}"
        try:
            approval_doc = self.agent_store_container.read_item(item=approval_id, partition_key=pk)
            approval_doc["status"] = "approved" if approved else "rejected"
            approval_doc["decision"] = {
                "approved": approved,
                "decidedAt": datetime.now(UTC).isoformat(),
            }
            self.agent_store_container.upsert_item(approval_doc)
            logger.info(
                "Tool call %s in run %s %s",
                tool_call_id,
                run_id,
                "approved" if approved else "rejected",
            )
        except CosmosResourceNotFoundError:
            logger.warning("Approval document %s not found", approval_id)

    def get_tool_call_approval(self, run_id: str, tool_call_id: str) -> bool | None:
        """Get tool call approval status."""
        # Get run to find partition info
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return None

        run_doc = items[0]
        conversation_id = run_doc["conversationId"]
        user_id = run_doc["userId"]
        tenant_id = run_doc["tenantId"]
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        approval_id = f"appr_{run_id}_{tool_call_id}"
        try:
            approval_doc = self.agent_store_container.read_item(item=approval_id, partition_key=pk)
            decision = approval_doc.get("decision")
            if decision:
                return decision.get("approved")
            return None
        except CosmosResourceNotFoundError:
            return None

    def get_pending_tool_call(self, run_id: str, tool_call_id: str) -> ToolCall | None:
        """Get a pending tool call."""
        # Get run to find partition info
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return None

        run_doc = items[0]
        conversation_id = run_doc["conversationId"]
        user_id = run_doc["userId"]
        tenant_id = run_doc["tenantId"]
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        approval_id = f"appr_{run_id}_{tool_call_id}"
        try:
            approval_doc = self.agent_store_container.read_item(item=approval_id, partition_key=pk)
            if approval_doc.get("status") == "pending":
                # Reconstruct ToolCall from approval document
                # Note: We need to store the full arguments somewhere
                # For now, return a basic ToolCall
                return ToolCall(
                    id=approval_doc["toolCallId"],
                    name=approval_doc["toolName"],
                    arguments_json=approval_doc.get("request", {}).get("argumentsPreview", "{}"),
                )
        except CosmosResourceNotFoundError:
            return None

        return None

    def cancel_run(self, run_id: str) -> None:
        """Cancel a run."""
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise ValueError(f"Run {run_id} not found")

        run_doc = items[0]
        run_doc["status"] = "cancelled"
        run_doc["completedAt"] = datetime.now(UTC).isoformat()
        pk = self._build_partition_key(
            run_doc["tenantId"], run_doc["userId"], run_doc["conversationId"]
        )
        self.agent_store_container.upsert_item(run_doc)
        logger.info("Cancelled run %s", run_id)

    def is_cancelled(self, run_id: str) -> bool:
        """Check if a run is cancelled."""
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return False

        return items[0].get("status") == "cancelled"

    def complete_run(self, run_id: str) -> None:
        """Mark a run as completed."""
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise ValueError(f"Run {run_id} not found")

        run_doc = items[0]
        run_doc["status"] = "completed"
        run_doc["completedAt"] = datetime.now(UTC).isoformat()
        pk = self._build_partition_key(
            run_doc["tenantId"], run_doc["userId"], run_doc["conversationId"]
        )
        self.agent_store_container.upsert_item(run_doc)

    def error_run(self, run_id: str) -> None:
        """Mark a run as error."""
        query = "SELECT * FROM c WHERE c.type = 'run' AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise ValueError(f"Run {run_id} not found")

        run_doc = items[0]
        run_doc["status"] = "error"
        run_doc["completedAt"] = datetime.now(UTC).isoformat()
        pk = self._build_partition_key(
            run_doc["tenantId"], run_doc["userId"], run_doc["conversationId"]
        )
        self.agent_store_container.upsert_item(run_doc)

    def store_file(
        self,
        file_id: str,
        file_data: FileUploadResponse,
        conversation_id: str | None = None,
        run_id: str | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> None:
        """Store file metadata as artifact document.

        Args:
            file_id: File ID
            file_data: File upload response data
            conversation_id: Conversation ID (optional)
            run_id: Run ID (optional)
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)
        """
        tenant_id = tenant_id or self.default_tenant_id

        # If conversation_id not provided, we need to create a default one
        # or store without conversation context
        if not conversation_id:
            import uuid
            conversation_id = f"conv_{uuid.uuid4().hex[:16]}"

        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        now = datetime.now(UTC).isoformat()

        artifact_doc = {
            "id": file_id,
            "pk": pk,
            "type": "artifact",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "artifactType": "file",
            "source": "user_upload",
            "name": file_data.filename,
            "mimeType": file_data.content_type,
            "sizeBytes": file_data.size,
            "createdAt": now,
            "runId": run_id,
            "storage": {
                "provider": "blob",
                "container": "agent-files",
                "blobPath": f"{tenant_id}/{user_id}/{conversation_id}/{file_id}/{file_data.filename}",
            },
            "hash": None,
        }

        try:
            self.agent_store_container.upsert_item(artifact_doc)
        except Exception as e:
            logger.error("Error storing file metadata: %s", e)
            raise

    def get_file(self, file_id: str, user_id: str = "default", tenant_id: str | None = None) -> FileUploadResponse | None:
        """Get file metadata.

        Args:
            file_id: File ID
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            FileUploadResponse or None if not found
        """
        tenant_id = tenant_id or self.default_tenant_id

        # Query for artifact document (may need cross-partition query)
        query = "SELECT * FROM c WHERE c.type = 'artifact' AND c.id = @file_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@file_id", "value": file_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return None

        artifact_doc = items[0]
        return FileUploadResponse(
            file_id=file_id,
            filename=artifact_doc["name"],
            content_type=artifact_doc.get("mimeType", ""),
            size=artifact_doc.get("sizeBytes", 0),
        )

    # ========================================================================
    # Additional Query Methods
    # ========================================================================

    def get_conversation(
        self, conversation_id: str, user_id: str = "default", tenant_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get conversation document by ID.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            Conversation document or None
        """
        tenant_id = tenant_id or self.default_tenant_id
        return self._get_conversation_doc(tenant_id, user_id, conversation_id)

    def get_messages_paginated(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get paginated messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of message documents
        """
        tenant_id = tenant_id or self.default_tenant_id
        return self._query_by_type(tenant_id, user_id, conversation_id, "message", "seq", limit, offset)

    def get_conversation_messages_as_chat_messages(
        self,
        conversation_id: str,
        limit: int = 6,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[ChatMessage]:
        """Get last N messages for a conversation as ChatMessage objects.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return (default: 6 for 3 pairs)
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of ChatMessage objects, ordered by sequence (oldest first)
        """
        tenant_id = tenant_id or self.default_tenant_id
        
        # Get messages ordered by seq DESC (most recent first), then reverse to get oldest first
        messages = self._query_by_type(tenant_id, user_id, conversation_id, "message", "seq", limit, 0)
        
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        # Convert to ChatMessage format
        result = []
        for msg_doc in messages:
            # Extract text content from content array
            content_text = ""
            if msg_doc.get("content"):
                for content_item in msg_doc["content"]:
                    if content_item.get("type") == "text":
                        content_text += content_item.get("text", "")
            
            result.append(
                ChatMessage(
                    role=msg_doc["role"],
                    content=content_text,
                    file_ids=[],  # TODO: Extract from message if stored
                )
            )
        
        return result

    def get_runs(
        self,
        conversation_id: str,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all runs for a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of run documents
        """
        tenant_id = tenant_id or self.default_tenant_id
        return self._query_by_type(tenant_id, user_id, conversation_id, "run", "runSeq")

    def get_pending_approvals(
        self,
        conversation_id: str,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get pending approvals for a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of pending approval documents
        """
        tenant_id = tenant_id or self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        query = (
            "SELECT * FROM c WHERE c.pk = @pk AND c.type = @type AND c.status = @status "
            "ORDER BY c.requestedAt DESC"
        )
        parameters = [
            {"name": "@pk", "value": pk},
            {"name": "@type", "value": "toolApproval"},
            {"name": "@status", "value": "pending"},
        ]
        items = list(
            self.agent_store_container.query_items(query=query, parameters=parameters, partition_key=pk)
        )
        return items

    def get_artifacts(
        self,
        conversation_id: str,
        run_id: str | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get artifacts for a conversation, optionally filtered by run.

        Args:
            conversation_id: Conversation ID
            run_id: Optional run ID to filter by
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of artifact documents
        """
        tenant_id = tenant_id or self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        query = "SELECT * FROM c WHERE c.pk = @pk AND c.type = @type"
        parameters = [
            {"name": "@pk", "value": pk},
            {"name": "@type", "value": "artifact"},
        ]

        if run_id:
            query += " AND c.runId = @run_id"
            parameters.append({"name": "@run_id", "value": run_id})

        query += " ORDER BY c.createdAt DESC"

        items = list(
            self.agent_store_container.query_items(query=query, parameters=parameters, partition_key=pk)
        )
        return items
