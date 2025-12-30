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

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Get schema for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool schema dictionary or None if tool not found
        """
        for tool in self.get_responses_api_tools_schema():
            if tool["name"] == tool_name:
                return tool
        return None

    def validate_parameters(self, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate tool parameters and identify missing required parameters.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments dictionary

        Returns:
            Tuple of (is_valid, missing_parameters)
            - is_valid: True if all required parameters are present
            - missing_parameters: List of missing required parameter names
        """
        schema = self.get_tool_schema(tool_name)
        if not schema:
            return False, []

        parameters_schema = schema.get("parameters", {})
        required = parameters_schema.get("required", [])

        missing = []
        for param_name in required:
            # Check if parameter is missing or None or empty string
            if param_name not in arguments or arguments[param_name] is None or arguments[param_name] == "":
                missing.append(param_name)

        return len(missing) == 0, missing

    def get_parameter_info(self, tool_name: str, parameter_name: str) -> dict[str, Any] | None:
        """Get information about a specific parameter from tool schema.

        Args:
            tool_name: Name of the tool
            parameter_name: Name of the parameter

        Returns:
            Parameter info dictionary (type, description, etc.) or None if not found
        """
        schema = self.get_tool_schema(tool_name)
        if not schema:
            return None

        parameters_schema = schema.get("parameters", {})
        properties = parameters_schema.get("properties", {})
        return properties.get(parameter_name)

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
