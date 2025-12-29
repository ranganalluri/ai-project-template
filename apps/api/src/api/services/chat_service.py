"""Chat service for handling streaming conversations."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from api.config import Settings
from api.services.foundry_client import FoundryClient
from api.services.tool_registry import tool_registry
from common.models.chat import ChatMessage, ToolCall
from common.services.chat_store import ChatStore
from openai.types.responses import EasyInputMessage, ResponseStreamEvent

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat streaming with tool approval."""

    def __init__(
        self,
        foundry_client: FoundryClient,
        settings: Settings,
        chat_store: ChatStore,
    ) -> None:
        """Initialize chat service.

        Args:
            foundry_client: Foundry client instance
            settings: Application settings
            chat_store: Chat store instance
        """
        self.foundry_client = foundry_client
        self.settings = settings
        self.chat_store = chat_store

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
            # Check if cancelled
            if self.chat_store.is_cancelled(run_id):
                yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"})
                return

            # Get OpenAI client
            client = self.foundry_client.get_openai_client()

            # Convert messages to Responses API format
            responses_messages = self._convert_messages_for_responses_api(messages, file_ids)

            # Get tools schema for Responses API
            tools = tool_registry.get_responses_api_tools_schema()

            # Stream completion using Responses API
            stream = client.responses.create(
                model=self.settings.foundry_deployment_name,
                input=responses_messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
            )

            current_content = ""
            current_tool_calls: dict[str, dict[str, Any]] = {}  # item_id -> tool_call_data
            current_function_arguments: dict[str, str] = {}  # item_id -> accumulated arguments

            async for event in self._async_stream(stream):
                if self.chat_store.is_cancelled(run_id):
                    yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"})
                    return

                # Handle different event types from Responses API
                event_type = getattr(event, "type", None)

                # Handle text delta events
                if event_type == "response.output_text.delta":
                    delta_text = getattr(event, "delta", "")
                    current_content += delta_text
                    yield self._format_sse_event(
                        "message_delta",
                        {"runId": run_id, "deltaText": delta_text},
                    )

                # Handle text done events
                elif event_type == "response.output_text.done":
                    text = getattr(event, "text", "")
                    if text and not current_content:
                        # If we haven't accumulated content, use the done text
                        current_content = text

                # Handle function call arguments delta
                elif event_type == "response.function_call_arguments.delta":
                    item_id = getattr(event, "item_id", "")
                    delta = getattr(event, "delta", "")
                    if item_id:
                        if item_id not in current_function_arguments:
                            current_function_arguments[item_id] = ""
                        current_function_arguments[item_id] += delta

                # Handle function call arguments done
                elif event_type == "response.function_call_arguments.done":
                    item_id = getattr(event, "item_id", "")
                    name = getattr(event, "name", "")
                    arguments = getattr(event, "arguments", "")

                    if item_id and name:
                        # Store the complete function call
                        current_tool_calls[item_id] = {
                            "id": item_id,  # Will be updated when we get the output_item.added event
                            "name": name,
                            "arguments": arguments,
                        }

                # Handle output item added (function calls)
                elif event_type == "response.output_item.added":
                    # This contains the complete function call with call_id
                    item = getattr(event, "item", None)
                    if item:
                        item_type = getattr(item, "type", None)
                        if item_type == "function_call":
                            item_id = getattr(item, "id", "")
                            call_id = getattr(item, "call_id", "")
                            name = getattr(item, "name", "")
                            arguments = getattr(item, "arguments", "")

                            if item_id and name:
                                # Update or create the tool call with the call_id
                                current_tool_calls[item_id] = {
                                    "id": call_id or item_id,
                                    "name": name,
                                    "arguments": arguments,
                                }

                # Handle errors
                elif event_type == "response.error":
                    error_msg = getattr(event, "message", "Unknown error")
                    yield self._format_sse_event("error", {"runId": run_id, "message": error_msg})
                    return

                # Handle completion
                elif event_type == "response.completed":
                    # Response is complete
                    break

            # Handle completed message
            if current_content:
                message = ChatMessage(role="assistant", content=current_content)
                self.chat_store.add_message(run_id, message)
                event_data = {"runId": run_id, "message": {"role": "assistant", "content": current_content}}
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
                yield self._format_sse_event("message_done", event_data)

            # Handle tool calls
            for item_id, tool_call_data in current_tool_calls.items():
                if tool_call_data.get("id") and tool_call_data.get("name"):
                    tool_call = ToolCall(
                        id=tool_call_data["id"],
                        name=tool_call_data["name"],
                        arguments_json=tool_call_data.get("arguments", ""),
                    )

                    # Add to pending tool calls
                    self.chat_store.add_pending_tool_call(run_id, tool_call)

                    # Emit tool call requested event
                    yield self._format_sse_event(
                        "tool_call_requested",
                        {
                            "runId": run_id,
                            "toolCall": {
                                "id": tool_call.id,
                                "name": tool_call.name,
                                "argumentsJson": tool_call.arguments_json,
                            },
                        },
                    )

                    # Wait for approval
                    approval = None
                    max_wait = 300  # 5 minutes timeout
                    wait_time = 0
                    while approval is None and wait_time < max_wait:
                        await asyncio.sleep(0.5)
                        wait_time += 0.5
                        approval = self.chat_store.get_tool_call_approval(run_id, tool_call.id)

                        if self.chat_store.is_cancelled(run_id):
                            yield self._format_sse_event("error", {"runId": run_id, "message": "Run was cancelled"})
                            return

                    if approval is None:
                        # Timeout - reject
                        approval = False

                    if approval:
                        # Execute tool
                        try:
                            result = await tool_registry.execute_tool(tool_call.name, tool_call.arguments_json)
                            result_json = json.dumps(result)

                            # Add tool result to messages with tool_call_id
                            tool_result_message = ChatMessage(
                                role="tool",
                                content=result_json,
                            )
                            # Store tool_call_id in message for OpenAI format
                            setattr(tool_result_message, "tool_call_id", tool_call.id)
                            self.chat_store.add_message(run_id, tool_result_message)

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
                            updated_messages = self.chat_store.get_messages(run_id)
                            # Convert to Responses API format for the next call
                            responses_messages2 = self._convert_messages_for_responses_api(updated_messages, file_ids)

                            # Make another streaming call with tool result using Responses API
                            stream2 = client.responses.create(
                                model=self.settings.foundry_deployment_name,
                                input=responses_messages2,
                                tools=tools,
                                tool_choice="auto",
                                stream=True,
                            )

                            current_content2 = ""
                            current_tool_calls2: dict[str, dict[str, Any]] = {}
                            current_function_arguments2: dict[str, str] = {}

                            async for event2 in self._async_stream(stream2):
                                if self.chat_store.is_cancelled(run_id):
                                    yield self._format_sse_event(
                                        "error", {"runId": run_id, "message": "Run was cancelled"}
                                    )
                                    return

                                event_type2 = getattr(event2, "type", None)

                                if event_type2 == "response.output_text.delta":
                                    delta_text2 = getattr(event2, "delta", "")
                                    current_content2 += delta_text2
                                    yield self._format_sse_event(
                                        "message_delta",
                                        {"runId": run_id, "deltaText": delta_text2},
                                    )
                                elif event_type2 == "response.output_text.done":
                                    text2 = getattr(event2, "text", "")
                                    if text2 and not current_content2:
                                        current_content2 = text2
                                elif event_type2 == "response.function_call_arguments.delta":
                                    item_id2 = getattr(event2, "item_id", "")
                                    delta2 = getattr(event2, "delta", "")
                                    if item_id2:
                                        if item_id2 not in current_function_arguments2:
                                            current_function_arguments2[item_id2] = ""
                                        current_function_arguments2[item_id2] += delta2
                                elif event_type2 == "response.function_call_arguments.done":
                                    item_id2 = getattr(event2, "item_id", "")
                                    name2 = getattr(event2, "name", "")
                                    arguments2 = getattr(event2, "arguments", "")
                                    if item_id2 and name2:
                                        current_tool_calls2[item_id2] = {
                                            "id": item_id2,
                                            "name": name2,
                                            "arguments": arguments2,
                                        }
                                elif event_type2 == "response.output_item.added":
                                    item2 = getattr(event2, "item", None)
                                    if item2:
                                        item_type2 = getattr(item2, "type", None)
                                        if item_type2 == "function_call":
                                            item_id2 = getattr(item2, "id", "")
                                            call_id2 = getattr(item2, "call_id", "")
                                            name2 = getattr(item2, "name", "")
                                            arguments2 = getattr(item2, "arguments", "")
                                            if item_id2 and name2:
                                                current_tool_calls2[item_id2] = {
                                                    "id": call_id2 or item_id2,
                                                    "name": name2,
                                                    "arguments": arguments2,
                                                }
                                elif event_type2 == "response.error":
                                    error_msg2 = getattr(event2, "message", "Unknown error")
                                    yield self._format_sse_event("error", {"runId": run_id, "message": error_msg2})
                                    return
                                elif event_type2 == "response.completed":
                                    break

                            # Handle completed message from tool result
                            if current_content2:
                                message2 = ChatMessage(role="assistant", content=current_content2)
                                self.chat_store.add_message(run_id, message2)
                                event_data = {
                                    "runId": run_id,
                                    "message": {
                                        "role": "assistant",
                                        "content": current_content2,
                                    },
                                }
                                if conversation_id:
                                    event_data["conversationId"] = conversation_id
                                yield self._format_sse_event("message_done", event_data)

                            # Handle any new tool calls from the continuation
                            for tool_call_data2 in current_tool_calls2.values():
                                if tool_call_data2.get("id") and tool_call_data2.get("name"):
                                    # Process tool calls recursively (simplified - in production,
                                    # handle multiple tool calls)
                                    break
                                    # For now, break after first tool call to avoid infinite recursion

                        except Exception as e:
                            logger.error(f"Error executing tool {tool_call.name}: {e}")
                            yield self._format_sse_event(
                                "error",
                                {"runId": run_id, "message": f"Tool execution error: {e!s}"},
                            )
                    else:
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
    ) -> list[EasyInputMessage]:
        """Convert messages to Responses API format using EasyInputMessage.

        The Responses API expects EasyInputMessage objects with roles:
        "user", "assistant", "system", or "developer".

        Args:
            messages: List of chat messages
            file_ids: List of attached file IDs

        Returns:
            List of EasyInputMessage objects
        """
        responses_messages: list[EasyInputMessage] = []

        # Add system message with file context if files are attached
        if file_ids:
            file_context = "The user has attached the following files: " + ", ".join(file_ids)
            responses_messages.append(
                EasyInputMessage(
                    role="system",
                    content=file_context,
                    type="message",
                )
            )

        for msg in messages:
            # Map roles - Responses API supports: user, assistant, system, developer
            # Note: "tool" role is not supported in EasyInputMessage, so we skip tool messages
            # Tool outputs should be handled differently in the Responses API
            if msg.role == "tool":
                # Tool messages are not directly supported in EasyInputMessage
                # They should be converted to function_call_output items or handled separately
                # For now, skip tool messages as they need special handling
                continue
            elif msg.role in ["user", "assistant", "system"]:
                responses_messages.append(
                    EasyInputMessage(
                        role=msg.role,  # type: ignore
                        content=msg.content,
                        type="message",
                    )
                )
            else:
                # Unknown role, skip or log warning
                logger.warning(f"Unknown role '{msg.role}' in message, skipping")

        return responses_messages

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
