"""
Calculator Tool — Phase 4.

A safe mathematical expression evaluator that supports basic arithmetic:
  +  -  *  /  **  ( )

Uses Python's `ast` module to parse the expression into an AST and then
walks the tree node-by-node, only allowing numeric literals and the
approved binary/unary operators. This approach is vastly safer than
eval() because no built-in functions, imports, attribute access,
or arbitrary code can execute.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

from app.tools.base import BaseTool, ToolResult

# Allowed binary operators mapped to their safe implementations
_BINARY_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# Allowed unary operators (e.g., -5, +3)
_UNARY_OPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Safety limits
_MAX_EXPONENT = 1000
_MAX_EXPRESSION_LENGTH = 200


def _safe_eval_node(node: ast.AST) -> float:
    """Recursively evaluate an AST node, allowing only safe operations.

    Raises:
        ValueError: If the node contains unsupported/dangerous constructs.
    """
    # Numeric literal (int or float)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    # Binary operation: left OP right
    if isinstance(node, ast.BinOp):
        op_func = _BINARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")

        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)

        # Guard against excessively large exponents
        if isinstance(node.op, ast.Pow):
            if abs(right) > _MAX_EXPONENT:
                raise ValueError(
                    f"Exponent too large (max {_MAX_EXPONENT}). "
                    f"Got {right}."
                )

        # Guard against division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv)) and right == 0:
            raise ValueError("Division by zero is not allowed.")

        return op_func(left, right)

    # Unary operation: -x, +x
    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_func(_safe_eval_node(node.operand))

    # Anything else is rejected
    raise ValueError(
        f"Unsupported expression element: {type(node).__name__}. "
        "Only numeric literals and arithmetic operators (+, -, *, /, **, %, //) are allowed."
    )


def safe_calculate(expression: str) -> float:
    """Evaluate a mathematical expression safely.

    Args:
        expression: A string containing a mathematical expression,
                    e.g. '25 * 4', '2 ** 10', '(3 + 5) / 2'.

    Returns:
        The computed float result.

    Raises:
        ValueError: If the expression is invalid, empty, too long,
                    or contains unsupported constructs.
    """
    if not expression or not expression.strip():
        raise ValueError("Expression cannot be empty.")

    expression = expression.strip()

    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError(
            f"Expression is too long (max {_MAX_EXPRESSION_LENGTH} characters)."
        )

    # Replace common user-friendly notation
    expression = expression.replace("^", "**")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid mathematical expression: {exc.msg}") from exc

    return _safe_eval_node(tree.body)


class CalculatorTool(BaseTool):
    """Safe arithmetic calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluate a mathematical expression safely. "
            "Supports: +, -, *, /, ** (power), % (modulo), // (floor division), "
            "and parentheses for grouping."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The arithmetic expression to evaluate, e.g. '25 * 4'.",
                }
            },
            "required": ["expression"],
        }

    def execute(self, expression: str) -> ToolResult:
        """Execute the calculator and return a ToolResult."""
        try:
            value = safe_calculate(expression)

            # Format the result nicely: show as int when there is no fractional part
            if value == int(value) and abs(value) < 1e15:
                formatted = str(int(value))
            else:
                formatted = str(value)

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=formatted,
            )
        except ValueError as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                result=str(exc),
            )
        except (OverflowError, ZeroDivisionError) as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                result=f"Calculation error: {exc}",
            )
