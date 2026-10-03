"""
Base Tool abstraction — Phase 4.

Provides the abstract base class that all tools must implement.
Each tool declares its own metadata (name, description, input schema)
and a synchronous `execute` method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Structured output from a tool execution."""

    tool_name: str = Field(
        ...,
        description="Name of the tool that produced this result.",
    )
    success: bool = Field(
        ...,
        description="Whether the tool execution succeeded.",
    )
    result: str = Field(
        ...,
        description="The output of the tool execution (result or error message).",
    )


class BaseTool(ABC):
    """Abstract base class for all tools.

    Tools are deterministic utilities (e.g. calculator, converter)
    that agents can invoke to augment their responses. Tools must
    NOT access the network, filesystem, environment variables,
    subprocesses, or any other external resource.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique, lowercase identifier for this tool (e.g. 'calculator')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON-Schema-style dictionary describing the expected input."""

    @abstractmethod
    def execute(self, expression: str) -> ToolResult:
        """Run the tool with the given input and return a ToolResult.

        Args:
            expression: The raw input string for the tool.

        Returns:
            A ToolResult indicating success/failure and the output.
        """
