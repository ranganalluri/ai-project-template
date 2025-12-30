"""Tool registry for MCP/tool calls."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from common.services.user_service import UserService

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self, user_service: UserService | None = None) -> None:
        """Initialize tool registry.

        Args:
            user_service: Optional UserService instance for search_users tool
        """
        self.user_service = user_service
        self.tools = {
            "search_users": self._search_users,
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
                "name": "search_users",
                "type": "function",
                "description": "Search for users by name. REQUIRES: 'name' parameter (string) containing the user's name to search for. Extract the name from the user's message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "REQUIRED: The name of the user to search for. Extract this from the user's message - look for any person's name (first name, last name, or full name) mentioned by the user.",
                        },
                    },
                    "required": ["name"],
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

    async def _search_users(self, name: str) -> dict[str, Any]:
        """Search Users.

        Args:
            name: Name of the user to search for

        Returns:
            Search results with user information
        """
        if self.user_service:
            # Use real implementation with UserService
            users = self.user_service.search_users(name)
            results = [
                {
                    "user_id": user.user_id,
                    "name": user.name,
                    "email": user.email,
                }
                for user in users
            ]
            logger.info("Found %d users matching '%s'", len(results), name)
            return {
                "query": name,
                "results": results,
            }
        else:
            # Fall back to dummy implementation for backward compatibility
            logger.warning("UserService not available, using dummy search_users implementation")
            return {
                "query": name,
                "results": [
                    {"title": "Sample User 1", "snippet": f"Content related to {name}"},
                    {"title": "Sample User 2", "snippet": f"More content about {name}"},
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


# Global tool registry instance (backward compatibility)
# For production use, use get_tool_registry() from api.services
tool_registry = ToolRegistry()


def get_tool_registry(user_service: UserService | None = None) -> ToolRegistry:
    """Get or create ToolRegistry instance with optional UserService.

    Args:
        user_service: Optional UserService instance for search_users tool

    Returns:
        ToolRegistry instance
    """
    return ToolRegistry(user_service=user_service)
