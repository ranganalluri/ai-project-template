"""Chat service for handling streaming conversations."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from api.config import Settings
from api.services.file_processor import FileProcessor
from api.services.foundry_client import FoundryClient
from api.services.tool_registry import ToolRegistry, tool_registry
from common.models.chat import ChatMessage, ToolCall
from common.services.chat_store import ChatStore
from common.services.file_storage import FileStorage
from common.services.instructions import AgentInstructions
from openai.types.responses import EasyInputMessage, ResponseStreamEvent

logger = logging.getLogger(__name__)


class StreamState:
    """Helper class to hold stream processing state."""

    def __init__(self) -> None:
        """Initialize stream state."""
        self.current_content: str = ""
        self.current_tool_calls: dict[str, dict[str, Any]] = {}  # item_id -> tool_call_data
        self.current_function_arguments: dict[str, str] = {}  # item_id -> accumulated arguments
        self.usage_data: dict[str, Any] | None = None  # LLM usage data from response
        self.response_id: str | None = None  # OpenAI response ID
        self.output_message_ids: list[str] | None = None  # Output message IDs


class ChatService:
    """Service for handling chat streaming with tool approval."""

    def __init__(
        self,
        foundry_client: FoundryClient,
        settings: Settings,
        chat_store: ChatStore,
        file_storage: FileStorage,
        tool_registry_instance: ToolRegistry | None = None,
    ) -> None:
        """Initialize chat service.

        Args:
            foundry_client: Foundry client instance
            settings: Application settings
            chat_store: Chat store instance
            file_storage: File storage instance
            tool_registry_instance: Optional ToolRegistry instance (defaults to global tool_registry)
        """
        self.foundry_client = foundry_client
        self.settings = settings
        self.chat_store = chat_store
        self.file_storage = file_storage
        self.tool_registry = tool_registry_instance if tool_registry_instance is not None else tool_registry

    def _ensure_conversation_id(self, run_id: str, conversation_id: str | None) -> str:
        """Ensure conversation_id is available, fetching it if needed.

        Args:
            run_id: Response ID
            conversation_id: Optional conversation ID

        Returns:
            conversation_id (resolved if needed)

        Raises:
            ValueError: If conversation_id cannot be determined
        """
        if conversation_id:
            return conversation_id
        # Get from run_id
        conv_id = self.chat_store.get_conversation_id_from_run(run_id)
        if not conv_id:
            raise ValueError(f"Could not determine conversation_id for run {run_id}")
        return conv_id

    async def stream_chat(
        self,
        run_id: str,
        messages: list[ChatMessage],
        file_ids: list[str],
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion with tool approval support.

        Args:
            run_id: Run ID
            messages: List of messages
            file_ids: List of attached file IDs
            conversation_id: Conversation ID to include in responses

        Yields:
            SSE event strings
        """
        try:
            # Resolve conversation_id if not provided (do this once at the start)
            conversation_id = self._ensure_conversation_id(run_id, conversation_id)

            # Check if cancelled
            if self.chat_store.is_cancelled(run_id, conversation_id=conversation_id):
                yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"})
                return

            # Get OpenAI client
            client = self.foundry_client.get_openai_client()

            # Get tools schema for Responses API
            tools = self.tool_registry.get_responses_api_tools_schema()
            chat_history = self.chat_store.get_messages(run_id, conversation_id=conversation_id)
            # chat_history = chat_history + messages
            chat_history_messages = self._convert_messages_for_responses_api(chat_history, file_ids)
            # Stream completion using Responses API
            stream = client.responses.create(
                model=self.settings.foundry_deployment_name,
                instructions=AgentInstructions.AGENT_INSTRUCTIONS,
                input=chat_history_messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
                store=self.settings.openai_responses_store,
            )

            # Process initial stream
            state = StreamState()
            async for sse_event, stream_state in self._process_stream(stream, run_id, conversation_id):
                state = stream_state  # Update state from stream processing
                if sse_event:
                    yield sse_event
                    # Check if it was an error event that should stop processing
                    if "error" in sse_event:
                        return

            # Store usage data and IDs if available
            if state.usage_data or hasattr(state, "response_id") or hasattr(state, "output_message_ids"):
                try:
                    logger.info(
                        "Storing usage data and IDs for run %s: usage_data=%s, response_id=%s, output_message_ids=%s",
                        run_id,
                        state.usage_data,
                        getattr(state, "response_id", None),
                        getattr(state, "output_message_ids", None),
                    )
                    self.chat_store.update_response_usage(
                        run_id,
                        state.usage_data or {},
                        conversation_id=conversation_id,
                        openai_response_id=getattr(state, "response_id", None),
                        output_message_ids=getattr(state, "output_message_ids", None),
                    )
                    logger.info("Successfully stored usage data and IDs for run %s", run_id)
                except Exception as e:
                    logger.error("Failed to store usage data and IDs for run %s: %s", run_id, e, exc_info=True)
                    # Don't fail the request if usage tracking fails
            else:
                logger.warning("No usage data or IDs available to store for run %s", run_id)

            # Handle completed message
            message_done_event = self._handle_message_completion(state, run_id, conversation_id)
            if message_done_event:
                yield message_done_event

            # Handle tool calls
            for item_id, tool_call_data in state.current_tool_calls.items():
                if tool_call_data.get("id") and tool_call_data.get("name"):
                    # Use accumulated arguments from delta events if available, otherwise use from done event
                    arguments_from_data = tool_call_data.get("arguments", "")
                    accumulated_args = state.current_function_arguments.get(item_id, "")
                    arguments_json = accumulated_args if accumulated_args else arguments_from_data

                    tool_call = ToolCall(
                        id=tool_call_data["id"],
                        name=tool_call_data["name"],
                        arguments_json=arguments_json,
                    )

                    # Add to pending tool calls and get partition key
                    partition_key = self.chat_store.add_pending_tool_call(
                        run_id, tool_call, conversation_id=conversation_id
                    )
                    if not partition_key:
                        logger.warning(
                            "Partition key not returned from add_pending_tool_call for tool call %s", tool_call.id
                        )

                    # Store function call in message history
                    try:
                        self.chat_store.add_function_call(
                            run_id=run_id,
                            call_id=tool_call.id,
                            name=tool_call.name,
                            arguments=tool_call.arguments_json,
                            conversation_id=conversation_id,
                        )
                    except Exception as e:
                        logger.warning("Failed to store function call in message history: %s", e)

                    # Validate parameters BEFORE emitting tool_call_requested event
                    try:
                        arguments = json.loads(tool_call.arguments_json) if tool_call.arguments_json else {}
                    except json.JSONDecodeError:
                        arguments = {}

                    is_valid, missing_params = self.tool_registry.validate_parameters(tool_call.name, arguments)

                    # If parameters are missing, request them from user BEFORE approval
                    if not is_valid and missing_params:
                        # Store parameter request
                        self.chat_store.request_parameters(
                            run_id, tool_call.id, missing_params, conversation_id=conversation_id
                        )

                        # Build parameter info for user
                        param_info = []
                        for param_name in missing_params:
                            param_schema = self.tool_registry.get_parameter_info(tool_call.name, param_name)
                            param_info.append(
                                {
                                    "name": param_name,
                                    "type": param_schema.get("type", "string") if param_schema else "string",
                                    "description": param_schema.get("description", "") if param_schema else "",
                                }
                            )

                        # Ask LLM to explain missing parameters
                        llm_explanations = await self._get_parameter_explanations(
                            run_id, tool_call, missing_params, param_info, conversation_id
                        )

                        # Add LLM explanations to parameter info
                        for param in param_info:
                            param_name = param["name"]
                            if param_name in llm_explanations:
                                param["llmExplanation"] = llm_explanations[param_name]

                        # Emit parameter request event
                        yield self._format_sse_event(
                            "parameter_request",
                            {
                                "runId": run_id,
                                "toolCallId": tool_call.id,
                                "toolName": tool_call.name,
                                "missingParameters": param_info,
                            },
                        )

                        # Wait for user to provide parameters
                        provided_params = None
                        max_wait = 300  # 5 minutes timeout
                        wait_time = 0
                        while provided_params is None and wait_time < max_wait:
                            await asyncio.sleep(5)
                            wait_time += 5

                            # Check if parameters have been provided
                            still_missing = self.chat_store.get_parameter_request(run_id, tool_call.id)
                            if still_missing is None:
                                # All parameters provided, get them from the store
                                provided_params = self.chat_store.get_provided_parameters(run_id, tool_call.id)
                                if provided_params:
                                    break

                            if self.chat_store.is_cancelled(run_id, conversation_id=conversation_id):
                                yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"})
                                return

                        if provided_params is None:
                            # Timeout - skip execution
                            yield self._format_sse_event(
                                "error",
                                {
                                    "runId": run_id,
                                    "message": f"Timeout waiting for parameters: {', '.join(missing_params)}",
                                },
                            )
                            continue

                        # Update tool call arguments with provided parameters
                        arguments.update(provided_params)
                        tool_call.arguments_json = json.dumps(arguments)

                    # Emit tool call requested event (after parameters are provided if needed)
                    # Always include partitionKey - it should always be set by add_pending_tool_call
                    if not partition_key:
                        logger.error(
                            "Partition key is missing for tool call %s in run %s - this should not happen",
                            tool_call.id,
                            run_id,
                        )
                    yield self._format_sse_event(
                        "tool_call_requested",
                        {
                            "runId": run_id,
                            "toolCall": {
                                "id": tool_call.id,
                                "name": tool_call.name,
                                "argumentsJson": tool_call.arguments_json,
                            },
                            "partitionKey": partition_key,
                        },
                    )

                    # Wait for approval
                    approval = None
                    max_wait = 300  # 5 minutes timeout
                    wait_time = 0
                    while approval is None and wait_time < max_wait:
                        await asyncio.sleep(5)
                        wait_time += 5
                        approval = self.chat_store.get_tool_call_approval(
                            run_id, tool_call.id, conversation_id=conversation_id
                        )
                        logger.warning("Approval for tool call %s in run %s: %s", tool_call.id, run_id, approval)
                        if self.chat_store.is_cancelled(run_id, conversation_id=conversation_id):
                            yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"})
                            return

                    if approval is None:
                        # Timeout - reject
                        approval = False

                    # Store approval/rejection decision in message history
                    # (This will be handled when we update get_messages to include approvals)

                    if approval:
                        # Parameters are already validated and provided, proceed with execution
                        # (Old parameter validation code removed - now done before approval)

                        # Execute tool
                        try:
                            result = await self.tool_registry.execute_tool(tool_call.name, tool_call.arguments_json)
                            result_json = json.dumps(result)

                            # Store function call output in message history
                            try:
                                self.chat_store.add_function_call_output(
                                    run_id=run_id,
                                    call_id=tool_call.id,
                                    output=result_json,
                                    conversation_id=conversation_id,
                                )
                            except Exception as e:
                                logger.warning("Failed to store function call output in message history: %s", e)
                                # If storing function call output fails, still add as regular message for backward compatibility
                                tool_result_message = ChatMessage(
                                    role="tool",
                                    content=result_json,
                                )
                                self.chat_store.add_message(
                                    run_id, tool_result_message, conversation_id=conversation_id
                                )

                            # Emit tool call result
                            yield self._format_sse_event(
                                "tool_call_result",
                                {
                                    "runId": run_id,
                                    "toolCallId": tool_call.id,
                                    "result": result,
                                },
                            )

                            # Continue with tool result - make another API call with updated messages
                            try:
                                # Pass conversation_id to filter messages and prevent duplicates if run_id exists in multiple conversations
                                try:
                                    updated_messages = self.chat_store.get_messages(
                                        run_id, conversation_id=conversation_id
                                    )
                                except Exception as db_error:
                                    error_msg = str(db_error)
                                    # Check if it's a Cosmos DB rate limit error
                                    if (
                                        "Too Many Requests" in error_msg
                                        or "429" in error_msg
                                        or "rate limit" in error_msg.lower()
                                    ):
                                        logger.error(
                                            "Cosmos DB rate limit error when getting messages for continuation: %s",
                                            error_msg,
                                        )
                                        yield self._format_sse_event(
                                            "error",
                                            {
                                                "runId": run_id,
                                                "message": "Database rate limit exceeded. Please wait a moment and try again.",
                                            },
                                        )
                                        return
                                    # Re-raise if it's not a rate limit error
                                    raise

                                # Convert to Responses API format for the next call
                                responses_messages2 = self._convert_messages_for_responses_api(
                                    updated_messages, file_ids
                                )

                                # Make another streaming call with tool result using Responses API
                                stream2 = client.responses.create(
                                    model=self.settings.foundry_deployment_name,
                                    instructions=AgentInstructions.AGENT_INSTRUCTIONS,
                                    input=responses_messages2,
                                    tools=tools,
                                    tool_choice="auto",
                                    stream=True,
                                    store=self.settings.openai_responses_store,
                                )

                                # Process continuation stream
                                state2 = StreamState()
                                async for sse_event2, stream_state2 in self._process_stream(
                                    stream2, run_id, conversation_id
                                ):
                                    state2 = stream_state2  # Update state from stream processing
                                    if sse_event2:
                                        yield sse_event2
                                        # Check if it was an error event that should stop processing
                                        if "error" in sse_event2:
                                            return

                                # Store usage data from continuation if available
                                if state2.usage_data:
                                    try:
                                        self.chat_store.update_response_usage(
                                            run_id, state2.usage_data, conversation_id=conversation_id
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            "Failed to store continuation usage data for run %s: %s",
                                            run_id,
                                            e,
                                            exc_info=True,
                                        )
                                        # Don't fail the request if usage tracking fails

                                # Handle completed message from tool result
                                # Always yield message_done even if content is empty (to signal completion)
                                message_done_event2 = self._handle_message_completion(
                                    state2, run_id, conversation_id, require_content=False
                                )
                                if message_done_event2:
                                    yield message_done_event2

                                # Handle any new tool calls from the continuation
                                for tool_call_data2 in state2.current_tool_calls.values():
                                    if tool_call_data2.get("id") and tool_call_data2.get("name"):
                                        # Process tool calls recursively (simplified - in production,
                                        # handle multiple tool calls)
                                        break
                                        # For now, break after first tool call to avoid infinite recursion
                            except Exception as continuation_error:
                                # Separate error handling for continuation API call
                                error_msg = str(continuation_error)
                                # Check if it's a Cosmos DB rate limit error
                                if (
                                    "Too Many Requests" in error_msg
                                    or "429" in error_msg
                                    or "rate limit" in error_msg.lower()
                                ):
                                    logger.error(
                                        "Cosmos DB rate limit error in continuation after tool %s: %s",
                                        tool_call.name,
                                        error_msg,
                                    )
                                    yield self._format_sse_event(
                                        "error",
                                        {
                                            "runId": run_id,
                                            "message": "Database rate limit exceeded when continuing conversation. Please wait a moment and try again.",
                                        },
                                    )
                                else:
                                    logger.error(
                                        "Error in continuation API call after tool %s: %s",
                                        tool_call.name,
                                        error_msg,
                                        exc_info=True,
                                    )
                                    yield self._format_sse_event(
                                        "error",
                                        {
                                            "runId": run_id,
                                            "message": f"Error continuing conversation after tool execution: {error_msg}",
                                        },
                                    )
                                # Don't re-raise - we've already yielded an error event

                        except Exception as e:
                            error_msg = str(e)
                            # Check if it's a Cosmos DB rate limit error
                            if (
                                "Too Many Requests" in error_msg
                                or "429" in error_msg
                                or "rate limit" in error_msg.lower()
                            ):
                                logger.error(
                                    "Cosmos DB rate limit error when executing tool %s: %s",
                                    tool_call.name,
                                    error_msg,
                                )
                                yield self._format_sse_event(
                                    "error",
                                    {
                                        "runId": run_id,
                                        "message": "Database rate limit exceeded. Please wait a moment and try again.",
                                    },
                                )
                            else:
                                logger.error(
                                    "Error executing tool %s or continuing conversation: %s",
                                    tool_call.name,
                                    error_msg,
                                    exc_info=True,
                                )
                                yield self._format_sse_event(
                                    "error",
                                    {"runId": run_id, "message": f"Tool execution error: {error_msg}"},
                                )
                    else:
                        # Tool call rejected - store rejection in message history
                        # Store a function call output with rejection status
                        try:
                            rejection_output = json.dumps({"status": "rejected", "reason": "User rejected tool call"})
                            self.chat_store.add_function_call_output(
                                run_id=run_id,
                                call_id=tool_call.id,
                                output=rejection_output,
                                conversation_id=conversation_id,
                            )
                        except Exception as e:
                            logger.warning("Failed to store function call rejection in message history: %s", e)

                        # Tool call rejected
                        yield self._format_sse_event(
                            "error",
                            {
                                "runId": run_id,
                                "message": f"Tool call {tool_call.name} was rejected",
                            },
                        )

            # Mark run as done
            self.chat_store.complete_run(run_id)
            event_data = {"runId": run_id}
            # Always include conversationId if available
            if conversation_id:
                event_data["conversationId"] = conversation_id
            else:
                # Try to get it from the run if not provided
                try:
                    conv_id = self.chat_store.get_conversation_id_from_run(run_id)
                    if conv_id:
                        event_data["conversationId"] = conv_id
                except Exception as e:
                    logger.warning("Could not get conversation_id for done event: %s", e)
            yield self._format_sse_event("done", event_data)

        except Exception as e:
            logger.error(f"Error in stream_chat: {e}", exc_info=True)
            self.chat_store.error_run(run_id)
            yield self._format_sse_event("error", {"runId": run_id, "message": str(e)})

    def _convert_messages(self, messages: list[ChatMessage], file_ids: list[str]) -> list[dict[str, Any]]:
        """Convert messages to OpenAI format.

        Args:
            messages: List of chat messages
            file_ids: List of attached file IDs

        Returns:
            List of OpenAI message dicts
        """
        openai_messages: list[dict[str, Any]] = []

        # Add system message with file context if files are attached
        if file_ids:
            file_context = "The user has attached the following files: " + ", ".join(file_ids)
            openai_messages.append({"role": "system", "content": file_context})

        for msg in messages:
            if msg.role == "tool":
                # Tool messages need special format
                openai_msg: dict[str, Any] = {
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": getattr(msg, "tool_call_id", ""),  # May not be present
                }
            else:
                openai_msg = {"role": msg.role, "content": msg.content}
            openai_messages.append(openai_msg)

        return openai_messages

    def _convert_messages_for_responses_api(
        self, messages: list[ChatMessage], file_ids: list[str]
    ) -> list[EasyInputMessage | dict[str, Any]]:
        """Convert messages to Responses API format, including function calls and outputs.

        The Responses API can accept:
        - EasyInputMessage objects for regular messages
        - Dictionary objects for function calls and function call outputs
        - Dictionary objects with content array when files are included

        Args:
            messages: List of chat messages (may include function calls in content_items)
            file_ids: List of attached file IDs

        Returns:
            List of EasyInputMessage objects and/or dictionaries for function calls/outputs
        """
        responses_messages: list[EasyInputMessage | dict[str, Any]] = []

        # Process files if present
        file_content_items: list[dict[str, Any]] = []
        if file_ids:
            for file_id in file_ids:
                file_item = FileProcessor.process_file(file_id, self.file_storage, self.chat_store)
                if file_item:
                    file_content_items.append(file_item)

        # First pass: convert all messages without files
        # We'll attach files to the last user message in a second pass
        for msg in messages:
            # Check if message has content_items with function calls or outputs
            if msg.content_items:
                for content_item in msg.content_items:
                    content_type = content_item.get("type")

                    if content_type == "function_call":
                        # Convert function call to Responses API format
                        responses_messages.append(
                            {
                                "type": "function_call",
                                "call_id": content_item.get("call_id", ""),
                                "name": content_item.get("name", ""),
                                "arguments": content_item.get("arguments", "{}"),
                            }
                        )
                    elif content_type == "function_call_output":
                        # Convert function call output to Responses API format
                        responses_messages.append(
                            {
                                "type": "function_call_output",
                                "call_id": content_item.get("call_id", ""),
                                "output": content_item.get("output", ""),
                            }
                        )
                    elif content_type == "text":
                        # Regular text message
                        text_content = content_item.get("text", "")
                        if msg.role in ["user", "assistant", "system"]:
                            # Convert all messages first, attach files later
                            responses_messages.append(
                                EasyInputMessage(
                                    role=msg.role,  # type: ignore
                                    content=text_content,
                                    type="message",
                                )
                            )
            else:
                # Legacy format - no content_items, use content string
                # Map roles - Responses API supports: user, assistant, system, developer
                if msg.role == "tool":
                    # Tool messages from legacy format - skip as they should be in content_items
                    logger.debug("Skipping legacy tool message without content_items")
                    continue
                elif msg.role in ["user", "assistant", "system"]:
                    # Convert all messages first, attach files later
                    responses_messages.append(
                        EasyInputMessage(
                            role=msg.role,  # type: ignore
                            content=msg.content,
                            type="message",
                        )
                    )
                else:
                    # Unknown role, skip or log warning
                    logger.warning("Unknown role '%s' in message, skipping", msg.role)

        # Second pass: Attach files to the last user message (most recent)
        if file_content_items:
            # Find the last user message in responses_messages
            last_user_index: int | None = None
            for i in range(len(responses_messages) - 1, -1, -1):
                msg = responses_messages[i]
                # Check if it's an EasyInputMessage with user role
                if hasattr(msg, "role") and msg.role == "user":
                    last_user_index = i
                    break
                # Check if it's a dict with user role
                elif isinstance(msg, dict) and msg.get("role") == "user":
                    last_user_index = i
                    break

            if last_user_index is not None:
                # Convert the last user message to content array format with files
                msg = responses_messages[last_user_index]
                if hasattr(msg, "content"):
                    # EasyInputMessage - convert to dict with content array
                    text_content = msg.content if isinstance(msg.content, str) else ""
                    responses_messages[last_user_index] = {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": text_content}
                        ] + file_content_items,
                    }
                elif isinstance(msg, dict):
                    # Already a dict
                    if isinstance(msg.get("content"), list):
                        # Already has content array, add files
                        msg["content"].extend(file_content_items)
                    else:
                        # Convert to content array format
                        text_content = msg.get("content", "")
                        msg["content"] = [
                            {"type": "input_text", "text": text_content}
                        ] + file_content_items
            else:
                # No user message found, create one with files
                content_array: list[dict[str, Any]] = []
                content_array.extend(file_content_items)
                responses_messages.append({"role": "user", "content": content_array})

        return responses_messages

    def _process_stream_event(
        self,
        event: Any,
        state: StreamState,
        run_id: str,
        conversation_id: str | None,
    ) -> tuple[str | None, bool, bool]:
        """Process a single stream event and update state.

        Args:
            event: Stream event from Responses API
            state: StreamState to update
            run_id: Run ID
            conversation_id: Optional conversation ID

        Returns:
            Tuple of (sse_event, should_continue, should_break)
            - sse_event: SSE event string to yield (None if nothing to yield)
            - should_continue: True to continue processing, False to return early
            - should_break: True to break from stream loop
        """
        event_type = getattr(event, "type", None)

        # Handle response.created event to capture OpenAI response ID
        if event_type == "response.created":
            openai_response_id = getattr(event, "response_id", None) or getattr(event, "id", None)
            if openai_response_id:
                try:
                    self.chat_store.update_response_openai_id(
                        run_id, openai_response_id, conversation_id=conversation_id
                    )
                except Exception as e:
                    logger.warning("Failed to store OpenAI response ID: %s", e)
            return None, True, False

        # Handle text delta events
        if event_type == "response.output_text.delta":
            delta_text = getattr(event, "delta", "")
            state.current_content += delta_text
            sse_event = self._format_sse_event(
                "message_delta",
                {"runId": run_id, "deltaText": delta_text},
            )
            return sse_event, True, False

        # Handle text done events
        if event_type == "response.output_text.done":
            text = getattr(event, "text", "")
            if text and not state.current_content:
                # If we haven't accumulated content, use the done text
                state.current_content = text
            return None, True, False

        # Handle function call arguments delta
        if event_type == "response.function_call_arguments.delta":
            item_id = getattr(event, "item_id", "")
            delta = getattr(event, "delta", "")
            if item_id:
                if item_id not in state.current_function_arguments:
                    state.current_function_arguments[item_id] = ""
                state.current_function_arguments[item_id] += delta
            return None, True, False

        # Handle function call arguments done
        if event_type == "response.function_call_arguments.done":
            item_id = getattr(event, "item_id", "")
            name = getattr(event, "name", "")
            arguments = getattr(event, "arguments", "")

            if item_id and name:
                # Use accumulated arguments from delta events if available, otherwise use from done event
                accumulated_args = state.current_function_arguments.get(item_id, "")
                final_arguments = accumulated_args if accumulated_args else arguments

                # Store the complete function call
                state.current_tool_calls[item_id] = {
                    "id": item_id,  # Will be updated when we get the output_item.added event
                    "name": name,
                    "arguments": final_arguments,
                }
            return None, True, False

        # Handle output item added (function calls)
        if event_type == "response.output_item.added":
            item = getattr(event, "item", None)
            if item:
                item_type = getattr(item, "type", None)
                if item_type == "function_call":
                    item_id = getattr(item, "id", "")
                    call_id = getattr(item, "call_id", "")
                    name = getattr(item, "name", "")
                    arguments = getattr(item, "arguments", "")

                    if item_id and name:
                        # Use accumulated arguments from delta events if available, otherwise use from added event
                        accumulated_args = state.current_function_arguments.get(item_id, "")
                        final_arguments = accumulated_args if accumulated_args else arguments

                        # Update or create the tool call with the call_id
                        state.current_tool_calls[item_id] = {
                            "id": call_id or item_id,
                            "name": name,
                            "arguments": final_arguments,
                        }
            return None, True, False

        # Handle errors
        if event_type == "response.error":
            error_msg = getattr(event, "message", "Unknown error")
            sse_event = self._format_sse_event("error", {"runId": run_id, "message": error_msg})
            return sse_event, False, False  # Should return early

        # Handle completion - extract usage data and IDs
        if event_type == "response.completed":
            # Get the response object - it might be the event itself or event.response
            response_obj = event
            if hasattr(event, "response"):
                response_obj = getattr(event, "response")

            # Extract response ID
            response_id = (
                getattr(response_obj, "id", None) or getattr(event, "id", None) or getattr(event, "response_id", None)
            )

            # Extract output message IDs from response object
            output_message_ids = None
            output = getattr(response_obj, "output", None) if hasattr(response_obj, "output") else None
            if not output and isinstance(response_obj, dict):
                output = response_obj.get("output")

            if output:
                output_message_ids = []
                # Handle list of output items
                if isinstance(output, list):
                    for item in output:
                        item_id = None
                        if hasattr(item, "id"):
                            item_id = getattr(item, "id")
                        elif isinstance(item, dict):
                            item_id = item.get("id")
                        if item_id:
                            output_message_ids.append(str(item_id))
                # Handle single output object
                elif hasattr(output, "id"):
                    output_message_ids.append(str(getattr(output, "id")))
                elif isinstance(output, dict) and "id" in output:
                    output_message_ids.append(str(output.get("id")))

                if not output_message_ids:
                    output_message_ids = None
                    logger.debug("No output message IDs found in response for run %s. Output: %s", run_id, output)

            # Extract usage data from the response object
            usage_data = self._extract_usage_data(event, run_id)
            if usage_data:
                state.usage_data = usage_data
                # Store response IDs along with usage data in a single operation
                state.response_id = response_id
                state.output_message_ids = output_message_ids
            return None, True, True  # Should break from loop

        return None, True, False

    async def _process_stream(
        self,
        stream: Any,
        run_id: str,
        conversation_id: str | None,
    ) -> AsyncGenerator[tuple[str | None, StreamState], None]:
        """Process a stream and yield SSE events.

        Args:
            stream: OpenAI Responses API stream
            run_id: Run ID
            conversation_id: Optional conversation ID

        Yields:
            Tuple of (sse_event, state) where sse_event is None or an SSE event string
        """
        state = StreamState()

        async for event in self._async_stream(stream):
            if self.chat_store.is_cancelled(run_id, conversation_id=conversation_id):
                yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"}), state
                return

            sse_event, should_continue, should_break = self._process_stream_event(event, state, run_id, conversation_id)

            if sse_event:
                yield sse_event, state

            if not should_continue:
                return

            if should_break:
                break

        # Always yield final state (even if no events were processed)
        yield None, state

    def _handle_message_completion(
        self,
        state: StreamState,
        run_id: str,
        conversation_id: str | None,
        require_content: bool = True,
    ) -> str | None:
        """Handle message completion and yield message_done event.

        Args:
            state: StreamState with completed content
            run_id: Run ID
            conversation_id: Optional conversation ID
            require_content: If True, only yield if content exists

        Returns:
            SSE event string or None
        """
        if require_content and not state.current_content:
            return None

        # Update response output text
        if state.current_content:
            self.chat_store.update_response_output(run_id, state.current_content, conversation_id=conversation_id)

        event_data: dict[str, Any] = {
            "runId": run_id,
            "message": {"role": "assistant", "content": state.current_content},
        }

        # Always include conversationId if available
        if conversation_id:
            event_data["conversationId"] = conversation_id
        else:
            # Try to get it from the run if not provided
            try:
                conv_id = self.chat_store.get_conversation_id_from_run(run_id)
                if conv_id:
                    event_data["conversationId"] = conv_id
            except Exception as e:
                logger.warning("Could not get conversation_id for message_done event: %s", e)

        return self._format_sse_event("message_done", event_data)

    async def _async_stream(self, stream: Any) -> AsyncGenerator[ResponseStreamEvent, None]:
        """Convert sync stream to async generator.

        Args:
            stream: OpenAI Responses API stream

        Yields:
            Response stream events
        """
        loop = asyncio.get_event_loop()

        def get_next_chunk():
            try:
                return next(stream)
            except StopIteration:
                return None

        while True:
            chunk = await loop.run_in_executor(None, get_next_chunk)
            if chunk is None:
                break
            yield chunk

    async def _get_parameter_explanations(
        self,
        run_id: str,
        tool_call: ToolCall,
        missing_params: list[str],
        param_info: list[dict[str, Any]],
        conversation_id: str | None = None,
    ) -> dict[str, str]:
        """Get LLM explanations for missing parameters.

        Args:
            run_id: Run ID
            tool_call: Tool call object
            missing_params: List of missing parameter names
            param_info: List of parameter info dictionaries
            conversation_id: Optional conversation ID

        Returns:
            Dictionary mapping parameter names to LLM explanations
        """
        try:
            # Get conversation context
            # Resolve conversation_id if needed
            resolved_conv_id = self._ensure_conversation_id(run_id, conversation_id)
            context_messages = self.chat_store.get_messages(run_id, conversation_id=resolved_conv_id)

            # Build prompt for LLM
            param_descriptions = []
            for param in param_info:
                param_descriptions.append(
                    f"- {param['name']} ({param['type']}): {param.get('description', 'No description')}"
                )

            system_prompt = (
                f"The assistant wants to call the tool '{tool_call.name}' but the following required parameters "
                f"are missing: {', '.join(missing_params)}.\n\n"
                f"Parameter details:\n" + "\n".join(param_descriptions) + "\n\n"
                "Based on the conversation context, please provide a brief, helpful explanation for each "
                "missing parameter that will help the user understand what value to provide. "
                "Format your response as a JSON object with parameter names as keys and explanations as values. "
                'For example: {"param1": "explanation for param1", "param2": "explanation for param2"}'
            )

            # Prepare messages for LLM
            llm_messages: list[EasyInputMessage] = [
                EasyInputMessage(role="system", content=system_prompt, type="message")
            ]

            # Add recent conversation context (last 5 messages for context)
            recent_messages = context_messages[-5:] if len(context_messages) > 5 else context_messages
            for msg in recent_messages:
                if msg.role in ["user", "assistant"]:
                    llm_messages.append(
                        EasyInputMessage(role=msg.role, content=msg.content, type="message")  # type: ignore
                    )

            # Make non-streaming LLM call
            client = self.foundry_client.get_openai_client()
            response = client.responses.create(
                model=self.settings.foundry_deployment_name,
                input=llm_messages,
                stream=False,
                store=self.settings.openai_responses_store,
            )

            # Extract and store usage data from non-streaming response
            usage_data = self._extract_usage_data(response, run_id)
            if usage_data and resolved_conv_id:
                try:
                    # Store usage data for parameter explanation call
                    # Note: This is a separate API call, so we track it separately
                    # For now, we'll merge it with the main response usage or log it
                    self.chat_store.update_response_usage(run_id, usage_data, conversation_id=resolved_conv_id)
                except Exception as e:
                    logger.warning(
                        "Failed to store parameter explanation usage data for run %s: %s", run_id, e, exc_info=True
                    )
                    # Don't fail if usage tracking fails

            # Extract explanation text
            explanation_text = ""
            if hasattr(response, "output") and response.output:
                if hasattr(response.output, "text"):
                    explanation_text = response.output.text
                elif isinstance(response.output, dict) and "text" in response.output:
                    explanation_text = response.output["text"]

            # Parse JSON response
            explanations: dict[str, str] = {}
            if explanation_text:
                try:
                    # Try to extract JSON from the response
                    explanation_text = explanation_text.strip()
                    # Remove markdown code blocks if present
                    if explanation_text.startswith("```"):
                        lines = explanation_text.split("\n")
                        explanation_text = "\n".join(lines[1:-1]) if len(lines) > 2 else explanation_text
                    explanations = json.loads(explanation_text)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse LLM explanation as JSON: {e}")
                    # Fallback: create a simple explanation from the text
                    for param_name in missing_params:
                        explanations[param_name] = explanation_text

            return explanations

        except Exception as e:
            logger.error(f"Error getting parameter explanations from LLM: {e}", exc_info=True)
            # Return empty dict on error - UI will fall back to schema descriptions
            return {}

    def _extract_usage_data(self, event: Any, run_id: str) -> dict[str, Any] | None:
        """Extract usage data from Responses API response object.

        Args:
            event: Response event object (response.completed or response object)
            run_id: Run ID for logging

        Returns:
            Dictionary with usage data or None if not available
        """
        try:
            usage_data: dict[str, Any] = {
                "provider": "openai",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Extract model/deployment name
            model = getattr(event, "model", None) or self.settings.foundry_deployment_name
            if model:
                usage_data["model"] = model

            # Extract response ID
            response_id = getattr(event, "response_id", None) or getattr(event, "id", None)
            if response_id:
                usage_data["responseId"] = response_id

            # Extract usage/token information
            # Try multiple ways to get usage object
            usage = None
            if hasattr(event, "usage"):
                usage = getattr(event, "usage", None)
            elif hasattr(event, "response") and hasattr(event.response, "usage"):
                usage = getattr(event.response, "usage", None)
            elif isinstance(event, dict):
                usage = event.get("usage") or (
                    event.get("response", {}).get("usage") if isinstance(event.get("response"), dict) else None
                )

            if usage:
                logger.debug("Found usage object for run %s, type: %s", run_id, type(usage).__name__)
                token_usage: dict[str, Any] = {}

                # Try different attribute names for token counts
                input_tokens = None
                output_tokens = None
                total_tokens = None

                # Try as object attributes first
                if hasattr(usage, "input_tokens"):
                    input_tokens = getattr(usage, "input_tokens")
                elif hasattr(usage, "inputTokens"):
                    input_tokens = getattr(usage, "inputTokens")
                elif hasattr(usage, "prompt_tokens"):
                    input_tokens = getattr(usage, "prompt_tokens")
                # Try as dict
                elif isinstance(usage, dict):
                    input_tokens = usage.get("input_tokens") or usage.get("inputTokens") or usage.get("prompt_tokens")

                # Try as object attributes first
                if hasattr(usage, "output_tokens"):
                    output_tokens = getattr(usage, "output_tokens")
                elif hasattr(usage, "outputTokens"):
                    output_tokens = getattr(usage, "outputTokens")
                elif hasattr(usage, "completion_tokens"):
                    output_tokens = getattr(usage, "completion_tokens")
                # Try as dict
                elif isinstance(usage, dict):
                    output_tokens = (
                        usage.get("output_tokens") or usage.get("outputTokens") or usage.get("completion_tokens")
                    )

                # Try as object attributes first
                if hasattr(usage, "total_tokens"):
                    total_tokens = getattr(usage, "total_tokens")
                elif hasattr(usage, "totalTokens"):
                    total_tokens = getattr(usage, "totalTokens")
                # Try as dict
                elif isinstance(usage, dict):
                    total_tokens = usage.get("total_tokens") or usage.get("totalTokens")

                logger.debug(
                    "Token extraction for run %s: input=%s, output=%s, total=%s",
                    run_id,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                )

                if input_tokens is not None:
                    token_usage["inputTokens"] = int(input_tokens)
                if output_tokens is not None:
                    token_usage["outputTokens"] = int(output_tokens)
                if total_tokens is not None:
                    token_usage["totalTokens"] = int(total_tokens)
                elif input_tokens is not None and output_tokens is not None:
                    token_usage["totalTokens"] = int(input_tokens) + int(output_tokens)

                if token_usage:
                    usage_data["tokenUsage"] = token_usage
                    logger.info("Extracted token usage for run %s: %s", run_id, token_usage)
                else:
                    logger.warning(
                        "Usage object found but no token counts extracted for run %s. Usage object: %s", run_id, usage
                    )
            else:
                logger.warning(
                    "No usage object found in event for run %s. Event type: %s, has usage attr: %s",
                    run_id,
                    type(event).__name__,
                    hasattr(event, "usage"),
                )

            # Only return usage_data if we have at least model or tokenUsage
            if "model" in usage_data or "tokenUsage" in usage_data:
                logger.info("Extracted usage data for run %s: %s", run_id, usage_data)
                return usage_data
            else:
                logger.warning("No usage data found in response for run %s", run_id)
                return None

        except Exception as e:
            logger.warning("Failed to extract usage data from response for run %s: %s", run_id, e, exc_info=True)
            return None

    def _format_sse_event(self, event_type: str, data: dict[str, Any]) -> str:
        """Format SSE event.

        Args:
            event_type: Event type
            data: Event data

        Returns:
            Formatted SSE event string
        """
        data_json = json.dumps(data)
        return f"event: {event_type}\ndata: {data_json}\n\n"
