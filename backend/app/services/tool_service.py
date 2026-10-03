"""
Tool Decision Service — Phase 4.

Determines whether a user message requires a tool and, if so, extracts
the tool input and executes it via the ToolRegistry.

The detection is deliberately simple and deterministic (keyword + regex
pattern matching) — no LLM call is made for the tool decision itself.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.tools.base import ToolResult
from app.tools.registry import get_registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns that signal a calculator request
# ---------------------------------------------------------------------------

# Explicit "calculate" keyword followed by content
_CALCULATE_PREFIX = re.compile(
    r"(?:calculate|compute|evaluate|solve)\s+(.+)",
    re.IGNORECASE,
)

# A standalone arithmetic expression (digits + operators + whitespace + parens only)
# Must contain at least one operator and one digit on each side.
_PURE_MATH_EXPR = re.compile(
    r"^[\d\s\+\-\*\/\^\.\(\)\%]+$"
)

# "What is <expr>?" pattern
_WHAT_IS_MATH = re.compile(
    r"(?:what\s+is|what's)\s+([\d\s\+\-\*\/\^\.\(\)\%]+)\s*\??$",
    re.IGNORECASE,
)

# "How much is <expr>?" pattern
_HOW_MUCH_MATH = re.compile(
    r"(?:how\s+much\s+is)\s+([\d\s\+\-\*\/\^\.\(\)\%]+)\s*\??$",
    re.IGNORECASE,
)


class ToolDecision(BaseModel):
    """The result of deciding whether a tool is needed."""

    tool_needed: bool = Field(
        ...,
        description="Whether a tool execution is required.",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Name of the tool to use, if any.",
    )
    tool_input: Optional[str] = Field(
        default=None,
        description="The extracted input for the tool.",
    )
    tool_result: Optional[ToolResult] = Field(
        default=None,
        description="The result from tool execution, if performed.",
    )


def _has_operator(text: str) -> bool:
    """Check that the text contains at least one arithmetic operator."""
    return any(op in text for op in ("+", "-", "*", "/", "^", "**"))


def _extract_calculator_expression(message: str) -> Optional[str]:
    """Try to extract a math expression from the user message.

    Returns the expression string if found, or None.
    """
    stripped = message.strip()

    # "Calculate 25 * 4"
    m = _CALCULATE_PREFIX.match(stripped)
    if m:
        expr = m.group(1).strip().rstrip("?.!")
        if _has_operator(expr):
            return expr

    # "What is 125 * 48?"
    m = _WHAT_IS_MATH.match(stripped)
    if m:
        expr = m.group(1).strip()
        if _has_operator(expr):
            return expr

    # "How much is 3 + 5?"
    m = _HOW_MUCH_MATH.match(stripped)
    if m:
        expr = m.group(1).strip()
        if _has_operator(expr):
            return expr

    # Pure math expression: "25 * 4"
    if _PURE_MATH_EXPR.match(stripped) and _has_operator(stripped):
        # Ensure it has at least one digit
        if re.search(r"\d", stripped):
            return stripped

    return None


async def decide_tool(user_message: str) -> ToolDecision:
    """Determine whether the user message requires a tool.

    Currently supports detection for:
    - calculator: arithmetic expressions

    Args:
        user_message: The raw user message.

    Returns:
        A ToolDecision indicating whether a tool is needed and the result.
    """
    expression = _extract_calculator_expression(user_message)

    if expression is None:
        return ToolDecision(tool_needed=False)

    registry = get_registry()
    calculator = registry.get("calculator")

    if calculator is None:
        logger.warning("Calculator tool is not registered — skipping tool execution.")
        return ToolDecision(tool_needed=False)

    logger.info("Tool decision: calculator needed for expression '%s'", expression)
    tool_result = calculator.execute(expression)

    return ToolDecision(
        tool_needed=True,
        tool_name="calculator",
        tool_input=expression,
        tool_result=tool_result,
    )
