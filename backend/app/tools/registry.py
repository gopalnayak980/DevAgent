"""
Tool Registry — Phase 4.

Central registry that holds all available tools. Tools are registered
at application startup and looked up by name at runtime.

The registry is deliberately kept independent of any LLM provider.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Thread-safe, singleton-style registry for tool instances."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Args:
            tool: The tool to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered. "
                "Duplicate registrations are not allowed."
            )
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> Optional[BaseTool]:
        """Look up a tool by name.

        Args:
            name: The unique name of the tool.

        Returns:
            The tool instance, or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        """Return metadata for all registered tools.

        Returns:
            A list of dicts with 'name' and 'description' for each tool.
        """
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------

_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Return the global tool registry singleton."""
    return _registry
