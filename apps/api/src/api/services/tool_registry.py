"""Tool registry for MCP/tool calls."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        """Initialize tool registry."""
        self.tools = {
            "search_docs": self._search_docs,
            "get_time": self._get_time,
        }

    def get_responses_api_tools_schema(self) -> list[dict[str, Any]]:
        """Get tools schema for Responses API (Azure AI SDK 2.0.0b2).

        The Responses API expects tools with 'name' at the top level.

        Returns:
            List of tool definitions in Responses API format
        """
        return [
            {
                "name": "search_docs",
                "type": "function",
                "description": "Search documentation for a query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_time",
                "type": "function",
                "description": "Get the current time",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    async def execute_tool(self, tool_name: str, arguments_json: str) -> Any:
        """Execute a tool.

        Args:
            tool_name: Name of the tool
            arguments_json: Tool arguments as JSON string

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not found
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        try:
            arguments = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError:
            arguments = {}

        tool_func = self.tools[tool_name]
        result = await tool_func(**arguments)
        logger.info(f"Executed tool {tool_name} with result: {result}")
        return result

    async def _search_docs(self, query: str) -> dict[str, Any]:
        """Search documentation (dummy implementation).

        Args:
            query: Search query

        Returns:
            Search results
        """
        # Dummy implementation
        return {
            "query": query,
            "results": [
                {"title": "Sample Doc 1", "snippet": f"Content related to {query}"},
                {"title": "Sample Doc 2", "snippet": f"More content about {query}"},
            ],
        }

    async def _get_time(self) -> dict[str, Any]:
        """Get current time (dummy implementation).

        Returns:
            Current time
        """
        return {
            "time": datetime.now(UTC).isoformat(),
            "timezone": "UTC",
        }


# Global tool registry instance
tool_registry = ToolRegistry()
