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
    ChatMessage,
    FileUploadResponse,
    ToolCall,
)

logger = logging.getLogger(__name__)


class ChatStore(ABC):
    """Abstract interface for chat store."""

    @abstractmethod
    def create_run(self, thread_id: str | None = None) -> tuple[str, str]:
        """Create a new run.

        Returns:
            Tuple of (run_id, conversation_id)
        """

    @abstractmethod
    def add_message(self, run_id: str, message: ChatMessage, conversation_id: str | None = None) -> None:
        """Add a message to a response.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            message: Message to add
            conversation_id: Optional conversation ID to filter by (prevents duplicates if run_id exists in multiple conversations)

        Note: Messages are now embedded in response.input array instead of creating separate documents.
        """

    @abstractmethod
    def get_messages(self, run_id: str, conversation_id: str | None = None) -> list[ChatMessage]:
        """Get all messages for a conversation, reconstructed from responses.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            conversation_id: Optional conversation ID to filter by (prevents duplicates if run_id exists in multiple conversations)

        Returns:
            List of ChatMessage objects reconstructed from responses and function calls.

        Note: Messages are now reconstructed from response.input, response.output, and function_call documents.
        """

    @abstractmethod
    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall, conversation_id: str | None = None) -> str:
        """Add a pending tool call.

        Args:
            run_id: Response ID
            tool_call: Tool call to add
            conversation_id: Optional conversation ID to avoid cross-partition queries

        Returns:
            Partition key for the function call document
        """

    @abstractmethod
    def approve_tool_call(
        self, run_id: str, tool_call_id: str, approved: bool, partition_key: str | None = None
    ) -> None:
        """Approve or reject a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            approved: Whether the tool call is approved
            partition_key: Optional partition key for the function call document
        """

    @abstractmethod
    def get_tool_call_approval(self, run_id: str, tool_call_id: str, conversation_id: str | None = None) -> bool | None:
        """Get tool call approval status.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            conversation_id: Optional conversation ID to avoid cross-partition queries

        Returns:
            Approval status (True/False) or None if pending
        """

    @abstractmethod
    def get_pending_tool_call(self, run_id: str, tool_call_id: str) -> ToolCall | None:
        """Get a pending tool call."""

    @abstractmethod
    def request_parameters(
        self, run_id: str, tool_call_id: str, missing_parameters: list[str], conversation_id: str | None = None
    ) -> None:
        """Request missing parameters for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            missing_parameters: List of missing parameter names
            conversation_id: Optional conversation ID to avoid cross-partition queries
        """

    @abstractmethod
    def get_parameter_request(self, run_id: str, tool_call_id: str) -> list[str] | None:
        """Get pending parameter request for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID

        Returns:
            List of missing parameter names, or None if no pending request
        """

    @abstractmethod
    def provide_parameters(self, run_id: str, tool_call_id: str, parameters: dict[str, Any]) -> None:
        """Provide parameters for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            parameters: Dictionary of parameter name -> value
        """

    @abstractmethod
    def get_provided_parameters(self, run_id: str, tool_call_id: str) -> dict[str, Any] | None:
        """Get provided parameters for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID

        Returns:
            Dictionary of provided parameters, or None if not found
        """

    @abstractmethod
    def cancel_run(self, run_id: str) -> None:
        """Cancel a run."""

    @abstractmethod
    def is_cancelled(self, run_id: str, conversation_id: str | None = None) -> bool:
        """Check if a run is cancelled.

        Args:
            run_id: Response ID
            conversation_id: Optional conversation ID to avoid cross-partition queries

        Returns:
            True if cancelled, False otherwise
        """

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

    @abstractmethod
    def get_responses(
        self,
        conversation_id: str,
        limit: int | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all responses for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of responses to return
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of response documents ordered by creation time
        """

    @abstractmethod
    def get_function_calls(
        self,
        response_id: str,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get function calls for a response.

        Args:
            response_id: Response ID
            status: Optional status filter ("pending", "approved", "rejected", "executed")
            conversation_id: Optional conversation ID for filtering

        Returns:
            List of function call documents
        """

    @abstractmethod
    def update_function_call_status(
        self,
        function_call_id: str,
        status: str,
        output: str | None = None,
        conversation_id: str | None = None,
    ) -> None:
        """Update function call status and optionally output.

        Args:
            function_call_id: Function call document ID
            status: New status ("pending", "approved", "rejected", "executed")
            output: Optional output JSON string (required when status is "executed")
            conversation_id: Optional conversation ID for filtering
        """

    @abstractmethod
    def add_function_call(
        self, run_id: str, call_id: str, name: str, arguments: str, conversation_id: str | None = None
    ) -> str:
        """Add a function call to a response.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            call_id: Function call ID (from LLM)
            name: Function/tool name
            arguments: Function arguments as JSON string
            conversation_id: Optional conversation ID to avoid cross-partition queries

        Returns:
            Function call document ID
        """

    @abstractmethod
    def update_response_usage(
        self,
        run_id: str,
        usage_data: dict[str, Any],
        conversation_id: str | None = None,
    ) -> None:
        """Update LLM usage data in response document.

        Args:
            run_id: Response ID
            usage_data: Dictionary containing usage information (provider, model, tokenUsage, etc.)
            conversation_id: Optional conversation ID for filtering
        """


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
        """Generate response ID with zero-padded format: resp_000004."""
        return f"resp_{seq:06d}"

    def _determine_conversation_id(self, thread_id: str | None) -> str:
        """Determine conversation_id from thread_id.

        Args:
            thread_id: Thread/conversation ID (can be None)

        Returns:
            Conversation ID (always starts with "conv_")
        """
        import uuid

        if thread_id:
            # Ensure conversation_id starts with "conv_"
            if not thread_id.startswith("conv_"):
                return f"conv_{thread_id}"
            else:
                return thread_id
        else:
            return f"conv_{uuid.uuid4().hex[:16]}"

    def _get_conversation_doc(self, tenant_id: str, user_id: str, conversation_id: str) -> dict[str, Any] | None:
        """Get conversation document by ID."""
        try:
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            doc = self.agent_store_container.read_item(item=conversation_id, partition_key=pk)
            return doc
        except CosmosResourceNotFoundError:
            return None

    def _get_or_create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        title: str | None = None,
        agent: dict[str, Any] | None = None,
        system: dict[str, Any] | None = None,
        max_retries: int = 5,
    ) -> dict[str, Any]:
        """Get or create conversation document atomically.

        Uses read-then-create pattern with retry on conflict to ensure
        the same conversation_id is only created once per thread_id.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            conversation_id: Conversation ID
            title: Optional conversation title
            agent: Optional agent configuration
            system: Optional system configuration
            max_retries: Maximum number of retries on conflict

        Returns:
            Conversation document
        """
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        now = datetime.now(UTC).isoformat()

        for attempt in range(max_retries):
            try:
                # Try to read existing conversation
                conv_doc = self._get_conversation_doc(tenant_id, user_id, conversation_id)
                if conv_doc:
                    # Update existing if needed
                    updated = False
                    if title and conv_doc.get("title") != title:
                        conv_doc["title"] = title
                        updated = True
                    if agent and conv_doc.get("agent") != agent:
                        conv_doc["agent"] = agent
                        updated = True
                    if system and conv_doc.get("system") != system:
                        conv_doc["system"] = system
                        updated = True
                    if updated:
                        conv_doc["updatedAt"] = now
                        # Remove _etag before upsert
                        if "_etag" in conv_doc:
                            etag = conv_doc.pop("_etag")
                        else:
                            etag = None
                        conv_doc["pk"] = pk
                        if etag:
                            self.agent_store_container.replace_item(
                                item=conversation_id,
                                body=conv_doc,
                                if_match=etag,
                            )
                        else:
                            self.agent_store_container.upsert_item(conv_doc)
                    return conv_doc

                # Create new conversation
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
                    "counters": {"responseSeq": 0},
                }
                self.agent_store_container.create_item(conv_doc)
                return conv_doc

            except CosmosAccessConditionFailedError:
                # ETag conflict or document already exists - retry
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2**attempt))
                    continue
                raise
            except Exception as e:
                # Check if it's a conflict error (document already exists)
                if "Conflict" in str(e) or "409" in str(e):
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (2**attempt))
                        continue
                logger.error("Error creating conversation: %s", e)
                raise

        raise Exception(f"Failed to create conversation after {max_retries} attempts")

    def _create_or_update_conversation(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        title: str | None = None,
        agent: dict[str, Any] | None = None,
        system: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update conversation document (legacy method, uses _get_or_create_conversation)."""
        return self._get_or_create_conversation(tenant_id, user_id, conversation_id, title, agent, system)

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
            counter_name: Counter name ('responseSeq' or legacy 'messageSeq'/'runSeq')
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
                    conv_doc = self._create_or_update_conversation(tenant_id, user_id, conversation_id)

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
                    time.sleep(0.1 * (2**attempt))
                    continue
                raise
            except Exception as e:
                logger.error("Error incrementing counter: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2**attempt))
                    continue
                raise

        raise Exception(f"Failed to increment counter after {max_retries} attempts")

    def _get_run_doc(self, tenant_id: str, user_id: str, conversation_id: str, run_id: str) -> dict[str, Any] | None:
        """Get response document by ID (backward compatibility: still called _get_run_doc)."""
        try:
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            # Support both "run" (old) and "response" (new) types for backward compatibility
            if doc.get("type") in ("run", "response"):
                return doc
            return None
        except CosmosResourceNotFoundError:
            return None

    def _get_partition_info_from_run_id(self, run_id: str) -> tuple[str, str, str] | None:
        """Get partition info (tenant_id, user_id, conversation_id) from run_id using minimal projection.

        Returns:
            Tuple of (tenant_id, user_id, conversation_id) or None if not found
        """
        # Use projection to only fetch needed fields (reduces RU consumption)
        query = "SELECT c.tenantId, c.userId, c.conversationId FROM c WHERE (c.type = 'response' OR c.type = 'run') AND c.id = @run_id"
        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=[{"name": "@run_id", "value": run_id}],
                enable_cross_partition_query=True,
            )
        )
        if not items:
            return None
        doc = items[0]
        return (doc["tenantId"], doc["userId"], doc["conversationId"])

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
        """Query documents by type within a partition.

        Optimized to use server-side pagination to reduce RU consumption.
        """
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        query = "SELECT * FROM c WHERE c.pk = @pk AND c.type = @type"

        if order_by:
            query += f" ORDER BY c.{order_by} DESC"

        # Use server-side pagination to reduce RU consumption
        if limit is not None:
            query += f" OFFSET {offset} LIMIT {limit}"
        elif offset > 0:
            query += f" OFFSET {offset}"

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

        return items

    def create_run(
        self, thread_id: str | None = None, user_id: str = "default", tenant_id: str | None = None
    ) -> tuple[str, str]:
        """Create a new run.

        Args:
            thread_id: Thread/conversation ID (used as conversation_id)
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            Tuple of (run_id, conversation_id)
        """
        tenant_id = tenant_id or self.default_tenant_id
        conversation_id = self._determine_conversation_id(thread_id)

        # Ensure conversation exists atomically (prevents duplicates for same thread_id)
        self._get_or_create_conversation(tenant_id, user_id, conversation_id)

        # Increment response counter
        response_seq = self._increment_counter(tenant_id, user_id, conversation_id, "responseSeq")
        run_id = self._generate_run_id(response_seq)
        now = datetime.now(UTC).isoformat()

        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        response_doc = {
            "id": run_id,
            "pk": pk,
            "type": "response",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "responseSeq": response_seq,
            "status": "running",
            "createdAt": now,
            "startedAt": now,
            "completedAt": None,
            "openaiResponseId": None,  # Will be set when OpenAI response is received
            "input": [],  # Input messages array (populated as messages are added)
            "output": {"text": "", "metadata": {}},  # Output text and metadata
            "llm": None,
            "stepsSummary": None,
            "error": None,
        }

        self.agent_store_container.create_item(response_doc)
        logger.info("Created response %s for conversation %s", run_id, conversation_id)
        return run_id, conversation_id

    def add_message(
        self,
        run_id: str,
        message: ChatMessage,
        conversation_id: str | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> None:
        """Add a message to a response.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            message: Message to add
            conversation_id: Optional conversation ID to filter by (prevents duplicates if run_id exists in multiple conversations)
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Note: Messages are now embedded in response.input array instead of creating separate documents.
        """
        tenant_id = tenant_id or self.default_tenant_id

        # If conversation_id is provided, use partition key for efficient query
        # Otherwise, query response document to get conversation_id, user_id, and tenant_id
        if conversation_id:
            # Use partition key for efficient query
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            try:
                response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
                if response_doc.get("type") not in ("response", "run"):
                    raise ValueError(f"Document {run_id} is not a response")
            except CosmosResourceNotFoundError:
                raise ValueError(f"Response {run_id} not found")
        else:
            # Fall back to cross-partition query if conversation_id not provided
            # Use projection to only fetch needed fields for partition key (reduces RU)
            query = "SELECT c.id, c.conversationId, c.userId, c.tenantId FROM c WHERE (c.type = 'response' OR c.type = 'run') AND c.id = @run_id"
            items = list(
                self.agent_store_container.query_items(
                    query=query,
                    parameters=[{"name": "@run_id", "value": run_id}],
                    enable_cross_partition_query=True,
                )
            )
            if not items:
                raise ValueError(f"Response {run_id} not found")
            response_doc = items[0]
            conversation_id = response_doc["conversationId"]
            user_id = response_doc["userId"]
            tenant_id = response_doc["tenantId"]
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            # Now read the full document using partition key (more efficient)
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)

        # Ensure response document has input array (for backward compatibility with old "run" documents)
        if "input" not in response_doc:
            response_doc["input"] = []

        # Create message object to append to input array
        input_message = {
            "role": message.role,
            "content": message.content,
        }
        # Add file_ids if present
        if message.file_ids:
            input_message["file_ids"] = message.file_ids

        # Append message to response.input array
        response_doc["input"].append(input_message)

        # Update response document
        # Remove _etag from body if present (it's metadata)
        if "_etag" in response_doc:
            etag = response_doc.pop("_etag")
        else:
            etag = response_doc.get("_etag")

        # Ensure partition key is in the document body
        response_doc["pk"] = pk

        # Update response document
        try:
            if etag:
                self.agent_store_container.replace_item(
                    item=run_id,
                    body=response_doc,
                    if_match=etag,
                )
            else:
                self.agent_store_container.upsert_item(response_doc)
            # logger.debug("Added message to response %s input array", run_id)
        except Exception as e:
            # If update fails, log and re-raise
            logger.error("Failed to add message to response %s: %s", run_id, e)
            raise

    def add_function_call(
        self,
        run_id: str,
        call_id: str,
        name: str,
        arguments: str,
        conversation_id: str | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> str:
        """Add a function call as a separate document.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            call_id: Function call ID (from LLM)
            name: Function/tool name
            arguments: Function arguments as JSON string
            conversation_id: Optional conversation ID to avoid cross-partition queries
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            Function call document ID
        """
        tenant_id = tenant_id or self.default_tenant_id

        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")
        now = datetime.now(UTC).isoformat()

        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Create function call document ID
        function_call_id = f"fc_{call_id}"

        # Create function call document
        function_call_doc = {
            "id": function_call_id,
            "pk": pk,
            "type": "function_call",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "responseId": run_id,
            "call_id": call_id,
            "name": name,
            "arguments": arguments,
            "status": "pending",
            "output": None,
            "createdAt": now,
            "approvedAt": None,
            "executedAt": None,
        }

        try:
            # Explicitly pass partition key to avoid cross-partition query issues
            self.agent_store_container.create_item(function_call_doc)
            # logger.debug("Added function call %s (call_id: %s) to response %s", function_call_id, call_id, run_id)
            return function_call_id
        except Exception as e:
            if "Conflict" in str(e) or "409" in str(e) or "duplicate" in str(e).lower():
                logger.error("Duplicate function call ID detected: %s", function_call_id)
                raise ValueError(f"Function call ID {function_call_id} already exists") from e
            raise

    def add_function_call_output(
        self,
        run_id: str,
        call_id: str,
        output: str,
        conversation_id: str | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> str:
        """Add function call output by updating existing function_call document.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            call_id: Function call ID (must match the call_id from add_function_call)
            output: Function output as JSON string
            conversation_id: Optional conversation ID to avoid cross-partition queries
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            Function call document ID
        """
        tenant_id = tenant_id or self.default_tenant_id

        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Find function call document by call_id and responseId
        function_call_id = f"fc_{call_id}"
        try:
            function_call_doc = self.agent_store_container.read_item(item=function_call_id, partition_key=pk)

            # Verify it's the correct function call
            if function_call_doc.get("type") != "function_call":
                raise ValueError(f"Document {function_call_id} is not a function_call")
            if function_call_doc.get("call_id") != call_id:
                raise ValueError(
                    f"Function call ID mismatch: expected {call_id}, got {function_call_doc.get('call_id')}"
                )
            if function_call_doc.get("responseId") != run_id:
                raise ValueError(f"Response ID mismatch: expected {run_id}, got {function_call_doc.get('responseId')}")

            # Update function call document
            now = datetime.now(UTC).isoformat()
            function_call_doc["status"] = "executed"
            function_call_doc["output"] = output
            function_call_doc["executedAt"] = now

            # Remove _etag if present
            if "_etag" in function_call_doc:
                etag = function_call_doc.pop("_etag")
            else:
                etag = function_call_doc.get("_etag")

            # Ensure partition key is in document
            function_call_doc["pk"] = pk

            # Update document
            if etag:
                self.agent_store_container.replace_item(
                    item=function_call_id,
                    body=function_call_doc,
                    if_match=etag,
                )
            else:
                self.agent_store_container.upsert_item(function_call_doc)

            # logger.debug("Updated function call %s (call_id: %s) with output for response %s", function_call_id, call_id, run_id)
            return function_call_id

        except CosmosResourceNotFoundError:
            raise ValueError(f"Function call {function_call_id} not found for call_id {call_id} in response {run_id}")

    def update_response_openai_id(
        self,
        run_id: str,
        openai_response_id: str,
        conversation_id: str | None = None,
    ) -> None:
        """Update OpenAI response ID in response document.

        Args:
            run_id: Response ID
            openai_response_id: OpenAI Responses API response ID
            conversation_id: Optional conversation ID for filtering
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        user_id = "default"  # Default, will be updated from doc
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            if response_doc.get("type") not in ("response", "run"):
                raise ValueError(f"Document {run_id} is not a response")
            # Update user_id and tenant_id from doc
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Update OpenAI response ID
        response_doc["openaiResponseId"] = openai_response_id

        # Remove _etag if present
        if "_etag" in response_doc:
            etag = response_doc.pop("_etag")
        else:
            etag = response_doc.get("_etag")

        # Ensure partition key is in document
        response_doc["pk"] = pk

        # Update document
        try:
            if etag:
                self.agent_store_container.replace_item(
                    item=run_id,
                    body=response_doc,
                    if_match=etag,
                )
            else:
                self.agent_store_container.upsert_item(response_doc)
        except Exception as e:
            logger.error("Failed to update response %s OpenAI ID: %s", run_id, e)
            raise

    def update_response_output_message_ids(
        self,
        run_id: str,
        output_message_ids: list[str],
        conversation_id: str | None = None,
    ) -> None:
        """Update output message IDs in response document.

        Args:
            run_id: Response ID
            output_message_ids: List of OpenAI output message IDs
            conversation_id: Optional conversation ID for filtering
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        user_id = "default"  # Default, will be updated from doc
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            if response_doc.get("type") not in ("response", "run"):
                raise ValueError(f"Document {run_id} is not a response")
            # Update user_id and tenant_id from doc
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Update output message IDs in metadata
        if "output" not in response_doc:
            response_doc["output"] = {"text": "", "metadata": {}}
        if not isinstance(response_doc["output"], dict):
            response_doc["output"] = {"text": str(response_doc["output"]), "metadata": {}}

        if "metadata" not in response_doc["output"]:
            response_doc["output"]["metadata"] = {}

        response_doc["output"]["metadata"]["outputMessageIds"] = output_message_ids

        # Remove _etag if present
        if "_etag" in response_doc:
            etag = response_doc.pop("_etag")
        else:
            etag = response_doc.get("_etag")

        # Ensure partition key is in document
        response_doc["pk"] = pk

        # Update document
        try:
            if etag:
                self.agent_store_container.replace_item(
                    item=run_id,
                    body=response_doc,
                    if_match=etag,
                )
            else:
                self.agent_store_container.upsert_item(response_doc)
        except Exception as e:
            logger.error("Failed to update response %s output message IDs: %s", run_id, e)
            raise

    def update_response_usage(
        self,
        run_id: str,
        usage_data: dict[str, Any],
        conversation_id: str | None = None,
        openai_response_id: str | None = None,
        output_message_ids: list[str] | None = None,
    ) -> None:
        """Update LLM usage data and optionally response IDs in response document.

        Args:
            run_id: Response ID
            usage_data: Dictionary containing usage information (provider, model, tokenUsage, etc.)
            conversation_id: Optional conversation ID for filtering
            openai_response_id: Optional OpenAI Responses API response ID
            output_message_ids: Optional list of OpenAI output message IDs
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        user_id = "default"  # Default, will be updated from doc
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            if response_doc.get("type") not in ("response", "run"):
                raise ValueError(f"Document {run_id} is not a response")
            # Update user_id and tenant_id from doc
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Update OpenAI response ID if provided
        if openai_response_id:
            response_doc["openaiResponseId"] = openai_response_id

        # Update output message IDs if provided
        if output_message_ids:
            if "output" not in response_doc:
                response_doc["output"] = {"text": "", "metadata": {}}
            if not isinstance(response_doc["output"], dict):
                response_doc["output"] = {"text": str(response_doc["output"]), "metadata": {}}

            if "metadata" not in response_doc["output"]:
                response_doc["output"]["metadata"] = {}

            response_doc["output"]["metadata"]["outputMessageIds"] = output_message_ids

        # Update LLM usage data - merge with existing if present
        existing_llm = response_doc.get("llm")
        logger.info(
            "Updating response usage for run %s. Existing llm: %s, New usage_data: %s", run_id, existing_llm, usage_data
        )

        if existing_llm and isinstance(existing_llm, dict):
            # Merge usage data, combining token counts
            merged_usage = existing_llm.copy()

            # Update fields from new usage_data
            merged_usage.update(usage_data)

            # Merge token usage if both exist
            if "tokenUsage" in existing_llm and "tokenUsage" in usage_data:
                existing_tokens = existing_llm.get("tokenUsage", {})
                new_tokens = usage_data.get("tokenUsage", {})
                merged_tokens = existing_tokens.copy()

                # Sum token counts
                for key in ["inputTokens", "outputTokens", "totalTokens"]:
                    existing_val = existing_tokens.get(key, 0) or 0
                    new_val = new_tokens.get(key, 0) or 0
                    merged_tokens[key] = existing_val + new_val

                merged_usage["tokenUsage"] = merged_tokens
            elif "tokenUsage" in usage_data:
                # If only new data has tokenUsage, use it
                merged_usage["tokenUsage"] = usage_data["tokenUsage"]

            usage_data = merged_usage

        response_doc["llm"] = usage_data
        logger.info("Final llm data to save for run %s: %s", run_id, usage_data)

        # Remove _etag if present
        if "_etag" in response_doc:
            etag = response_doc.pop("_etag")
        else:
            etag = response_doc.get("_etag")

        # Ensure partition key is in document
        response_doc["pk"] = pk

        # Update document
        try:
            if etag:
                self.agent_store_container.replace_item(
                    item=run_id,
                    body=response_doc,
                    if_match=etag,
                )
            else:
                self.agent_store_container.upsert_item(response_doc)
        except Exception as e:
            logger.error("Failed to update response %s usage data: %s", run_id, e)
            raise

    def update_response_output(
        self,
        run_id: str,
        output_text: str,
        conversation_id: str | None = None,
    ) -> None:
        """Update response output text.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)
            output_text: Output text to set
            conversation_id: Optional conversation ID for filtering
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        user_id = "default"  # Default, will be updated from doc
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            if response_doc.get("type") not in ("response", "run"):
                raise ValueError(f"Document {run_id} is not a response")
            # Update user_id and tenant_id from doc
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Ensure output field exists
        if "output" not in response_doc:
            response_doc["output"] = {"text": "", "metadata": {}}

        # Update output text
        response_doc["output"]["text"] = output_text

        # Remove _etag if present
        if "_etag" in response_doc:
            etag = response_doc.pop("_etag")
        else:
            etag = response_doc.get("_etag")

        # Ensure partition key is in document
        response_doc["pk"] = pk

        # Update document
        try:
            if etag:
                self.agent_store_container.replace_item(
                    item=run_id,
                    body=response_doc,
                    if_match=etag,
                )
            else:
                self.agent_store_container.upsert_item(response_doc)
            # logger.debug("Updated response %s output text", run_id)
        except Exception as e:
            logger.error("Failed to update response %s output: %s", run_id, e)
            raise

    def get_conversation_id_from_run(self, run_id: str) -> str | None:
        """Get conversation ID from a response ID (backward compatibility: still called get_conversation_id_from_run).

        Args:
            run_id: Response ID (kept as run_id for backward compatibility)

        Returns:
            Conversation ID or None if response not found
        """
        # Use projection to only fetch conversationId (reduces RU consumption)
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            return None
        return partition_info[2]  # conversation_id is the third element

    def get_messages(self, run_id: str, conversation_id: str | None = None) -> list[ChatMessage]:
        """Get all messages for a conversation, reconstructed from responses and function calls.

        Args:
            run_id: Response ID (kept as run_id for backward compatibility, optional if conversation_id provided)
            conversation_id: Optional conversation ID to filter by (prevents duplicates if run_id exists in multiple conversations)

        Returns:
            List of ChatMessage objects reconstructed from responses and function calls.

        Note: Messages are now reconstructed from response.input, response.output, and function_call documents.
        """
        # If conversation_id is provided, get user_id and tenant_id from conversation document
        # Otherwise, get from response document using run_id
        if conversation_id:
            # Get conversation document to find user_id and tenant_id
            # Use default values and get from first response if needed
            user_id = "default"
            tenant_id = self.default_tenant_id
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            try:
                conv_doc = self.agent_store_container.read_item(item=conversation_id, partition_key=pk)
                if conv_doc and conv_doc.get("type") == "conversation":
                    # Get user_id and tenant_id from conversation document
                    user_id = conv_doc.get("userId", "default")
                    tenant_id = conv_doc.get("tenantId", self.default_tenant_id)
            except CosmosResourceNotFoundError:
                # Conversation not found, try to get user_id and tenant_id from response document
                # But keep the provided conversation_id (don't overwrite it)
                if run_id:
                    # Use projection to only fetch needed fields (reduces RU)
                    partition_info = self._get_partition_info_from_run_id(run_id)
                    if not partition_info:
                        return []
                    response_tenant_id, response_user_id, response_conversation_id = partition_info
                    # Verify the response belongs to the provided conversation_id
                    if response_conversation_id != conversation_id:
                        return []
                    user_id = response_user_id
                    tenant_id = response_tenant_id
                else:
                    # No run_id provided, can't get user_id/tenant_id, return empty
                    return []
        else:
            # No conversation_id provided, must use run_id
            if not run_id:
                return []
            # Use projection to only fetch needed fields (reduces RU)
            partition_info = self._get_partition_info_from_run_id(run_id)
            if not partition_info:
                return []
            tenant_id, user_id, conversation_id = partition_info

        # Get all responses for this conversation (ordered by creation time)
        responses = self.get_responses(conversation_id, user_id=user_id, tenant_id=tenant_id)

        # Reconstruct messages from responses
        result = []
        for response in responses:
            # Extract input messages from response.input
            input_messages = response.get("input", [])
            for input_msg in input_messages:
                # Input messages are already in the correct format: {"role": "...", "content": "...", "file_ids": [...]}
                result.append(
                    ChatMessage(
                        role=input_msg.get("role", "user"),
                        content=input_msg.get("content", ""),
                        file_ids=input_msg.get("file_ids", []),  # Extract from stored message
                        content_items=None,
                    )
                )

            # Extract output text from response.output
            output_text = response.get("output", {}).get("text", "")
            if output_text:
                result.append(
                    ChatMessage(
                        role="assistant",
                        content=output_text,
                        file_ids=[],
                        content_items=None,
                    )
                )

            # Get function calls for this response (only executed ones for history)
            response_id = response.get("id")
            if response_id:
                function_calls = self.get_function_calls(
                    response_id=response_id,
                    status="executed",
                    conversation_id=conversation_id,
                )

                # Add function calls and outputs as content_items
                for fc in function_calls:
                    # Function call
                    result.append(
                        ChatMessage(
                            role="assistant",
                            content="",
                            file_ids=[],
                            content_items=[
                                {
                                    "type": "function_call",
                                    "call_id": fc.get("call_id"),
                                    "name": fc.get("name"),
                                    "arguments": fc.get("arguments", "{}"),
                                }
                            ],
                        )
                    )

                    # Function call output
                    if fc.get("output"):
                        result.append(
                            ChatMessage(
                                role="tool",
                                content=fc.get("output", ""),
                                file_ids=[],
                                content_items=[
                                    {
                                        "type": "function_call_output",
                                        "call_id": fc.get("call_id"),
                                        "output": fc.get("output", ""),
                                    }
                                ],
                            )
                        )

        return result

    def add_pending_tool_call(self, run_id: str, tool_call: ToolCall, conversation_id: str | None = None) -> str:
        """Add a pending tool call.

        Creates a function_call document with status="pending" and optionally a toolApproval document for workflow metadata.

        Args:
            run_id: Response ID
            tool_call: Tool call to add
            conversation_id: Optional conversation ID to avoid cross-partition queries

        Returns:
            Partition key for the function call document
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use default values and get from response if needed
        user_id = "default"
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Create function_call document with status="pending"
        # First check if function_call already exists (from add_function_call)
        function_call_id = f"fc_{tool_call.id}"
        try:
            function_call_doc = self.agent_store_container.read_item(item=function_call_id, partition_key=pk)
            # Update status to pending if it exists
            if function_call_doc.get("type") == "function_call":
                function_call_doc["status"] = "pending"
                if "_etag" in function_call_doc:
                    etag = function_call_doc.pop("_etag")
                else:
                    etag = function_call_doc.get("_etag")
                function_call_doc["pk"] = pk
                if etag:
                    self.agent_store_container.replace_item(
                        item=function_call_id,
                        body=function_call_doc,
                        if_match=etag,
                    )
                else:
                    self.agent_store_container.upsert_item(function_call_doc)
        except CosmosResourceNotFoundError:
            # Function call doesn't exist yet, create it
            now = datetime.now(UTC).isoformat()
            function_call_doc = {
                "id": function_call_id,
                "pk": pk,
                "type": "function_call",
                "tenantId": tenant_id,
                "userId": user_id,
                "conversationId": conversation_id,
                "responseId": run_id,
                "call_id": tool_call.id,
                "name": tool_call.name,
                "arguments": tool_call.arguments_json,
                "status": "pending",
                "output": None,
                "createdAt": now,
                "approvedAt": None,
                "executedAt": None,
            }
            # Explicitly pass partition key to avoid cross-partition query issues
            self.agent_store_container.create_item(function_call_doc)

        # Also create toolApproval document for workflow metadata (optional)
        approval_id = f"appr_{run_id}_{tool_call.id}"
        now = datetime.now(UTC).isoformat()
        approval_doc = {
            "id": approval_id,
            "pk": pk,
            "type": "toolApproval",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "responseId": run_id,
            "functionCallId": function_call_id,
            "runId": run_id,  # Keep for backward compatibility
            "toolCallId": tool_call.id,
            "toolName": tool_call.name,
            "request": {
                "summary": f"Tool call: {tool_call.name}",
                "riskLevel": "medium",
                "argumentsPreview": (
                    tool_call.arguments_json[:200] if len(tool_call.arguments_json) > 200 else tool_call.arguments_json
                ),
            },
            "status": "pending",
            "requestedAt": now,
            "expiresAt": None,
            "decision": None,
        }

        try:
            # Explicitly pass partition key to avoid cross-partition query issues
            self.agent_store_container.create_item(approval_doc)
        except Exception as e:
            # If approval document already exists, that's okay
            if "Conflict" not in str(e) and "409" not in str(e):
                logger.warning("Failed to create toolApproval document: %s", e)

        logger.info("Added pending tool call %s for response %s", tool_call.id, run_id)
        return pk

    def approve_tool_call(
        self, run_id: str, tool_call_id: str, approved: bool, partition_key: str | None = None
    ) -> None:
        """Approve or reject a tool call.

        Updates the function_call document status and optionally the toolApproval document.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            approved: Whether the tool call is approved
            partition_key: Optional partition key for the function call document
        """
        # Use provided partition key or get from response
        if partition_key:
            pk = partition_key
        else:
            # Get response to find partition info - use projection to reduce RU
            partition_info = self._get_partition_info_from_run_id(run_id)
            if not partition_info:
                raise ValueError(f"Response {run_id} not found")
            tenant_id, user_id, conversation_id = partition_info
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Update function_call document status
        function_call_id = f"fc_{tool_call_id}"
        try:
            function_call_doc = self.agent_store_container.read_item(item=function_call_id, partition_key=pk)
            if function_call_doc.get("type") == "function_call":
                now = datetime.now(UTC).isoformat()
                function_call_doc["status"] = "approved" if approved else "rejected"
                if approved:
                    function_call_doc["approvedAt"] = now

                if "_etag" in function_call_doc:
                    etag = function_call_doc.pop("_etag")
                else:
                    etag = function_call_doc.get("_etag")

                function_call_doc["pk"] = pk

                if etag:
                    self.agent_store_container.replace_item(
                        item=function_call_id,
                        body=function_call_doc,
                        if_match=etag,
                    )
                else:
                    self.agent_store_container.upsert_item(function_call_doc)
        except CosmosResourceNotFoundError:
            logger.warning("Function call document %s not found", function_call_id)

        # Also update toolApproval document if it exists (for workflow metadata)
        approval_id = f"appr_{run_id}_{tool_call_id}"
        try:
            approval_doc = self.agent_store_container.read_item(item=approval_id, partition_key=pk)
            approval_doc["status"] = "approved" if approved else "rejected"
            approval_doc["decision"] = {
                "approved": approved,
                "decidedAt": datetime.now(UTC).isoformat(),
            }
            self.agent_store_container.upsert_item(approval_doc)
        except CosmosResourceNotFoundError:
            # Approval document not found, that's okay
            pass

        logger.info(
            "Tool call %s in response %s %s",
            tool_call_id,
            run_id,
            "approved" if approved else "rejected",
        )

    def get_tool_call_approval(self, run_id: str, tool_call_id: str, conversation_id: str | None = None) -> bool | None:
        """Get tool call approval status.

        Checks the function_call document status first, falls back to toolApproval document.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            conversation_id: Optional conversation ID to avoid cross-partition queries

        Returns:
            Approval status (True/False) or None if pending
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use default values and get from response if needed
        user_id = "default"
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            return None

        # Check function_call document first
        function_call_id = f"fc_{tool_call_id}"
        try:
            function_call_doc = self.agent_store_container.read_item(item=function_call_id, partition_key=pk)
            if function_call_doc.get("type") == "function_call":
                status = function_call_doc.get("status")
                if status == "approved":
                    return True
                elif status == "rejected":
                    return False
                elif status == "executed":
                    return True  # Executed implies approved
                # status is "pending" or None
                return None
        except CosmosResourceNotFoundError:
            pass

        # Fall back to toolApproval document
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
        # Get response to find partition info - use projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            return None
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Find function call document
        function_call_id = f"fc_{tool_call_id}"
        try:
            function_call_doc = self.agent_store_container.read_item(item=function_call_id, partition_key=pk)
            if function_call_doc.get("type") == "function_call" and function_call_doc.get("status") == "pending":
                return ToolCall(
                    id=function_call_doc.get("call_id", tool_call_id),
                    name=function_call_doc.get("name", ""),
                    arguments_json=function_call_doc.get("arguments", "{}"),
                )
        except CosmosResourceNotFoundError:
            pass
        return None

    def request_parameters(
        self, run_id: str, tool_call_id: str, missing_parameters: list[str], conversation_id: str | None = None
    ) -> None:
        """Request missing parameters for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            missing_parameters: List of missing parameter names
            conversation_id: Optional conversation ID to avoid cross-partition queries
        """
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use default values and get from response if needed
        user_id = "default"
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            user_id = response_doc.get("userId", user_id)
            tenant_id = response_doc.get("tenantId", tenant_id)
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        except CosmosResourceNotFoundError:
            raise ValueError(f"Response {run_id} not found in conversation {conversation_id}")

        # Create or update parameter request document
        param_request_id = f"param_req_{run_id}_{tool_call_id}"
        now = datetime.now(UTC).isoformat()

        param_request_doc = {
            "id": param_request_id,
            "pk": pk,
            "type": "parameter_request",
            "tenantId": tenant_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "responseId": run_id,
            "toolCallId": tool_call_id,
            "missingParameters": missing_parameters,
            "providedParameters": {},
            "status": "pending",
            "createdAt": now,
            "updatedAt": now,
        }

        try:
            # Try to read existing document
            existing_doc = self.agent_store_container.read_item(item=param_request_id, partition_key=pk)
            if existing_doc.get("type") == "parameter_request":
                # Update existing document
                existing_doc["missingParameters"] = missing_parameters
                existing_doc["status"] = "pending"
                existing_doc["updatedAt"] = now
                self.agent_store_container.replace_item(item=param_request_id, body=existing_doc)
                return
        except CosmosResourceNotFoundError:
            pass

        # Create new document
        self.agent_store_container.create_item(param_request_doc)
        logger.info(
            "Requested parameters for tool call %s in run %s: %s",
            tool_call_id,
            run_id,
            missing_parameters,
        )

    def get_parameter_request(self, run_id: str, tool_call_id: str) -> list[str] | None:
        """Get pending parameter request for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID

        Returns:
            List of missing parameter names, or None if no pending request
        """
        # Get response to find partition info - use projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            return None
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        param_request_id = f"param_req_{run_id}_{tool_call_id}"
        try:
            param_request_doc = self.agent_store_container.read_item(item=param_request_id, partition_key=pk)
            if param_request_doc.get("type") == "parameter_request":
                status = param_request_doc.get("status")
                if status == "pending":
                    missing = param_request_doc.get("missingParameters", [])
                    provided = param_request_doc.get("providedParameters", {})
                    # Return only parameters that haven't been provided yet
                    still_missing = [p for p in missing if p not in provided]
                    return still_missing if still_missing else None
        except CosmosResourceNotFoundError:
            pass

        return None

    def provide_parameters(self, run_id: str, tool_call_id: str, parameters: dict[str, Any]) -> None:
        """Provide parameters for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID
            parameters: Dictionary of parameter name -> value
        """
        # Get response to find partition info - use projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            raise ValueError(f"Response {run_id} not found")
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        param_request_id = f"param_req_{run_id}_{tool_call_id}"
        now = datetime.now(UTC).isoformat()

        try:
            param_request_doc = self.agent_store_container.read_item(item=param_request_id, partition_key=pk)
            if param_request_doc.get("type") == "parameter_request":
                # Update provided parameters
                provided = param_request_doc.get("providedParameters", {})
                provided.update(parameters)
                param_request_doc["providedParameters"] = provided
                param_request_doc["updatedAt"] = now

                # Check if all missing parameters are now provided
                missing = param_request_doc.get("missingParameters", [])
                if all(p in provided for p in missing):
                    param_request_doc["status"] = "provided"
                else:
                    param_request_doc["status"] = "partial"

                self.agent_store_container.replace_item(item=param_request_id, body=param_request_doc)
                logger.info(
                    "Provided parameters for tool call %s in run %s: %s",
                    tool_call_id,
                    run_id,
                    list(parameters.keys()),
                )
        except CosmosResourceNotFoundError:
            # No parameter request found, create one
            missing = list(parameters.keys())
            param_request_doc = {
                "id": param_request_id,
                "pk": pk,
                "type": "parameter_request",
                "tenantId": tenant_id,
                "userId": user_id,
                "conversationId": conversation_id,
                "responseId": run_id,
                "toolCallId": tool_call_id,
                "missingParameters": missing,
                "providedParameters": parameters,
                "status": "provided" if missing else "pending",
                "createdAt": now,
                "updatedAt": now,
            }
            self.agent_store_container.create_item(param_request_doc)

    def get_provided_parameters(self, run_id: str, tool_call_id: str) -> dict[str, Any] | None:
        """Get provided parameters for a tool call.

        Args:
            run_id: Response ID
            tool_call_id: Tool call ID

        Returns:
            Dictionary of provided parameters, or None if not found
        """
        # Get response to find partition info - use projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            return None
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        param_request_id = f"param_req_{run_id}_{tool_call_id}"
        try:
            param_request_doc = self.agent_store_container.read_item(item=param_request_id, partition_key=pk)
            if param_request_doc.get("type") == "parameter_request":
                provided = param_request_doc.get("providedParameters", {})
                if provided:
                    return provided
        except CosmosResourceNotFoundError:
            pass

        return None

    def cancel_run(self, run_id: str) -> None:
        """Cancel a response (backward compatibility: still called cancel_run)."""
        # Get partition info using projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            raise ValueError(f"Run {run_id} not found")
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Read full document using partition key (more efficient)
        run_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
        run_doc["status"] = "cancelled"
        run_doc["completedAt"] = datetime.now(UTC).isoformat()
        run_doc["pk"] = pk
        self.agent_store_container.upsert_item(run_doc)
        logger.info("Cancelled run %s", run_id)

    def is_cancelled(self, run_id: str, conversation_id: str | None = None) -> bool:
        """Check if a response is cancelled."""
        # Require conversation_id - should be provided by chat_service
        if not conversation_id:
            raise ValueError("conversation_id is required")

        # Use partition key for efficient query
        user_id = "default"
        tenant_id = self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)
        try:
            response_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
            return response_doc.get("status") == "cancelled"
        except CosmosResourceNotFoundError:
            return False

    def complete_run(self, run_id: str) -> None:
        """Mark a response as completed (backward compatibility: still called complete_run)."""
        # Get partition info using projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            raise ValueError(f"Run {run_id} not found")
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Read full document using partition key (more efficient)
        run_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
        run_doc["status"] = "completed"
        run_doc["completedAt"] = datetime.now(UTC).isoformat()
        run_doc["pk"] = pk
        self.agent_store_container.upsert_item(run_doc)

    def error_run(self, run_id: str) -> None:
        """Mark a response as error (backward compatibility: still called error_run)."""
        # Get partition info using projection to reduce RU
        partition_info = self._get_partition_info_from_run_id(run_id)
        if not partition_info:
            raise ValueError(f"Run {run_id} not found")
        tenant_id, user_id, conversation_id = partition_info
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Read full document using partition key (more efficient)
        run_doc = self.agent_store_container.read_item(item=run_id, partition_key=pk)
        run_doc["status"] = "error"
        run_doc["completedAt"] = datetime.now(UTC).isoformat()
        run_doc["pk"] = pk
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
            "responseId": run_id,
            "runId": run_id,  # Keep for backward compatibility
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

    def get_file(
        self, file_id: str, user_id: str = "default", tenant_id: str | None = None
    ) -> FileUploadResponse | None:
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
        # Use projection to only fetch needed fields (reduces RU)
        query = "SELECT c.id, c.name, c.mimeType, c.sizeBytes FROM c WHERE c.type = 'artifact' AND c.id = @file_id"
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
                    file_ids=msg_doc.get("file_ids", []),  # Extract from stored message
                )
            )

        return result

    def get_responses(
        self,
        conversation_id: str,
        limit: int | None = None,
        user_id: str = "default",
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all responses for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of responses to return
            user_id: User ID (default: "default")
            tenant_id: Tenant ID (default: from settings)

        Returns:
            List of response documents ordered by creation time (oldest first)
        """
        tenant_id = tenant_id or self.default_tenant_id
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Query responses (ordered by createdAt ASC for chronological order)
        query = "SELECT * FROM c WHERE c.pk = @pk AND (c.type = 'response' OR c.type = 'run') ORDER BY c.createdAt ASC"
        parameters = [{"name": "@pk", "value": pk}]

        items = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=pk,
            )
        )

        if limit:
            items = items[:limit]

        return items

    def get_function_calls(
        self,
        response_id: str,
        status: str | None = None,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get function calls for a response.

        Args:
            response_id: Response ID
            status: Optional status filter ("pending", "approved", "rejected", "executed")
            conversation_id: Optional conversation ID for filtering

        Returns:
            List of function call documents
        """
        # Get response to find partition info
        # If conversation_id is provided, use partition key for efficient query
        if conversation_id:
            user_id = "default"  # Default, will be updated from doc
            tenant_id = self.default_tenant_id
            pk = self._build_partition_key(tenant_id, user_id, conversation_id)
            try:
                response_doc = self.agent_store_container.read_item(item=response_id, partition_key=pk)
                if response_doc.get("type") not in ("response", "run"):
                    return []
                items = [response_doc]
            except CosmosResourceNotFoundError:
                return []
        else:
            # Query by ID only - requires cross-partition query
            query = "SELECT * FROM c WHERE (c.type = 'response' OR c.type = 'run') AND c.id = @response_id"
            items = list(
                self.agent_store_container.query_items(
                    query=query,
                    parameters=[{"name": "@response_id", "value": response_id}],
                    enable_cross_partition_query=True,  # Required when querying by ID only
                )
            )

        if not items:
            return []

        response_doc = items[0]
        conversation_id = conversation_id or response_doc["conversationId"]
        user_id = response_doc["userId"]
        tenant_id = response_doc["tenantId"]
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Query function calls for this response
        query = "SELECT * FROM c WHERE c.pk = @pk AND c.type = @type AND c.responseId = @response_id"
        if status:
            query += " AND c.status = @status"

        parameters = [
            {"name": "@pk", "value": pk},
            {"name": "@type", "value": "function_call"},
            {"name": "@response_id", "value": response_id},
        ]
        if status:
            parameters.append({"name": "@status", "value": status})

        function_calls = list(
            self.agent_store_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=pk,
            )
        )

        # Sort by createdAt
        function_calls.sort(key=lambda x: x.get("createdAt", ""))
        return function_calls

    def update_function_call_status(
        self,
        function_call_id: str,
        status: str,
        output: str | None = None,
        conversation_id: str | None = None,
    ) -> None:
        """Update function call status and optionally output.

        Args:
            function_call_id: Function call document ID
            status: New status ("pending", "approved", "rejected", "executed")
            output: Optional output JSON string (required when status is "executed")
            conversation_id: Optional conversation ID for filtering
        """
        # Find function call document
        # If conversation_id provided, use it to get partition key
        if conversation_id:
            # Need to find the function call to get tenant_id and user_id
            # Query by function_call_id and conversation_id - use projection to reduce RU
            query = (
                "SELECT c.tenantId, c.userId, c.conversationId FROM c WHERE c.type = 'function_call' AND c.id = @function_call_id "
                "AND c.conversationId = @conversation_id"
            )
            items = list(
                self.agent_store_container.query_items(
                    query=query,
                    parameters=[
                        {"name": "@function_call_id", "value": function_call_id},
                        {"name": "@conversation_id", "value": conversation_id},
                    ],
                    enable_cross_partition_query=True,
                )
            )
        else:
            # Query without conversation_id (requires cross-partition query)
            # Use projection to only fetch needed fields for partition key (reduces RU)
            query = "SELECT c.tenantId, c.userId, c.conversationId FROM c WHERE c.type = 'function_call' AND c.id = @function_call_id"
            items = list(
                self.agent_store_container.query_items(
                    query=query,
                    parameters=[{"name": "@function_call_id", "value": function_call_id}],
                    enable_cross_partition_query=True,
                )
            )

        if not items:
            raise ValueError(f"Function call {function_call_id} not found")

        partition_info = items[0]
        conversation_id = conversation_id or partition_info["conversationId"]
        user_id = partition_info["userId"]
        tenant_id = partition_info["tenantId"]
        pk = self._build_partition_key(tenant_id, user_id, conversation_id)

        # Read full document using partition key (more efficient)
        function_call_doc = self.agent_store_container.read_item(item=function_call_id, partition_key=pk)

        # Update function call document
        now = datetime.now(UTC).isoformat()
        function_call_doc["status"] = status

        if status == "executed" and output:
            function_call_doc["output"] = output
            function_call_doc["executedAt"] = now
        elif status == "approved":
            function_call_doc["approvedAt"] = now
        elif status in ("rejected", "pending"):
            # Reset timestamps if needed
            pass

        # Remove _etag if present
        if "_etag" in function_call_doc:
            etag = function_call_doc.pop("_etag")
        else:
            etag = function_call_doc.get("_etag")

        # Ensure partition key is in document
        function_call_doc["pk"] = pk

        # Update document
        if etag:
            self.agent_store_container.replace_item(
                item=function_call_id,
                body=function_call_doc,
                if_match=etag,
            )
        else:
            self.agent_store_container.upsert_item(function_call_doc)

        # logger.debug("Updated function call %s status to %s", function_call_id, status)

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
        # Query both "response" and legacy "run" types for backward compatibility
        responses = self._query_by_type(tenant_id, user_id, conversation_id, "response", "responseSeq")
        legacy_runs = self._query_by_type(tenant_id, user_id, conversation_id, "run", "runSeq")
        # Combine and sort by sequence
        all_runs = responses + legacy_runs
        all_runs.sort(key=lambda x: x.get("responseSeq", x.get("runSeq", 0)))
        return all_runs

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
            "SELECT * FROM c WHERE c.pk = @pk AND c.type = @type AND c.status = @status " "ORDER BY c.requestedAt DESC"
        )
        parameters = [
            {"name": "@pk", "value": pk},
            {"name": "@type", "value": "toolApproval"},
            {"name": "@status", "value": "pending"},
        ]
        items = list(self.agent_store_container.query_items(query=query, parameters=parameters, partition_key=pk))
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

        items = list(self.agent_store_container.query_items(query=query, parameters=parameters, partition_key=pk))
        return items
