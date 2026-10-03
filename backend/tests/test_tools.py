"""
Tests for Phase 4 — Tool Calling.

Covers:
- Calculator tool: arithmetic operations, parentheses, edge cases, safety
- Tool registry: register, get, list, duplicate prevention
- Tool decision service: detection, extraction, non-tool passthrough
- Integration: calculator via registry, existing agents still work
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.tools.base import BaseTool, ToolResult
from app.tools.calculator import CalculatorTool, safe_calculate
from app.tools.registry import ToolRegistry, get_registry
from app.services.tool_service import decide_tool, _extract_calculator_expression


client = TestClient(app)


# ===========================================================================
# Calculator — safe_calculate() unit tests
# ===========================================================================

class TestCalculatorAddition:
    """Test calculator addition operations."""

    def test_simple_addition(self):
        assert safe_calculate("2 + 3") == 5.0

    def test_multi_addition(self):
        assert safe_calculate("1 + 2 + 3 + 4") == 10.0

    def test_large_addition(self):
        assert safe_calculate("999999 + 1") == 1000000.0


class TestCalculatorSubtraction:
    """Test calculator subtraction operations."""

    def test_simple_subtraction(self):
        assert safe_calculate("10 - 3") == 7.0

    def test_negative_result(self):
        assert safe_calculate("3 - 10") == -7.0

    def test_subtract_zero(self):
        assert safe_calculate("5 - 0") == 5.0


class TestCalculatorMultiplication:
    """Test calculator multiplication operations."""

    def test_simple_multiplication(self):
        assert safe_calculate("25 * 4") == 100.0

    def test_multiply_by_zero(self):
        assert safe_calculate("100 * 0") == 0.0

    def test_decimal_multiplication(self):
        assert safe_calculate("2.5 * 4") == 10.0


class TestCalculatorDivision:
    """Test calculator division operations."""

    def test_simple_division(self):
        assert safe_calculate("100 / 4") == 25.0

    def test_decimal_division(self):
        result = safe_calculate("10 / 3")
        assert abs(result - 3.3333333333) < 0.0001

    def test_division_by_zero_raises(self):
        with pytest.raises(ValueError, match="Division by zero"):
            safe_calculate("10 / 0")


class TestCalculatorParentheses:
    """Test calculator grouping with parentheses."""

    def test_simple_parens(self):
        assert safe_calculate("(2 + 3) * 4") == 20.0

    def test_nested_parens(self):
        assert safe_calculate("((2 + 3) * (4 - 1))") == 15.0

    def test_parens_division(self):
        assert safe_calculate("(10 + 20) / 5") == 6.0


class TestCalculatorPowers:
    """Test exponentiation."""

    def test_simple_power(self):
        assert safe_calculate("2 ** 10") == 1024.0

    def test_caret_notation(self):
        # ^ is converted to ** internally
        assert safe_calculate("2 ^ 10") == 1024.0

    def test_exponent_too_large(self):
        with pytest.raises(ValueError, match="Exponent too large"):
            safe_calculate("2 ** 10000")


class TestCalculatorInvalidInput:
    """Test invalid expressions are rejected."""

    def test_empty_expression(self):
        with pytest.raises(ValueError, match="empty"):
            safe_calculate("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            safe_calculate("   ")

    def test_invalid_syntax(self):
        with pytest.raises(ValueError, match="Invalid"):
            safe_calculate("2 +* 3")

    def test_too_long_expression(self):
        with pytest.raises(ValueError, match="too long"):
            safe_calculate("1 + " * 100)


class TestCalculatorDangerousExpressions:
    """Test that dangerous expressions are rejected."""

    def test_import_rejected(self):
        with pytest.raises(ValueError):
            safe_calculate("__import__('os')")

    def test_function_call_rejected(self):
        with pytest.raises(ValueError):
            safe_calculate("exec('print(1)')")

    def test_attribute_access_rejected(self):
        with pytest.raises(ValueError):
            safe_calculate("(1).__class__")

    def test_list_comprehension_rejected(self):
        with pytest.raises(ValueError):
            safe_calculate("[x for x in range(10)]")

    def test_string_rejected(self):
        with pytest.raises(ValueError):
            safe_calculate("'hello' + 'world'")

    def test_variable_name_rejected(self):
        with pytest.raises(ValueError):
            safe_calculate("x + 1")


# ===========================================================================
# CalculatorTool — execute() via the tool interface
# ===========================================================================

class TestCalculatorToolExecute:
    """Test the CalculatorTool wrapper."""

    def test_tool_metadata(self):
        tool = CalculatorTool()
        assert tool.name == "calculator"
        assert "expression" in tool.description.lower() or "math" in tool.description.lower()
        assert "expression" in str(tool.input_schema)

    def test_successful_execution(self):
        tool = CalculatorTool()
        result = tool.execute("25 * 4")
        assert result.success is True
        assert result.result == "100"
        assert result.tool_name == "calculator"

    def test_failed_execution(self):
        tool = CalculatorTool()
        result = tool.execute("invalid expression here")
        assert result.success is False
        assert result.tool_name == "calculator"

    def test_division_by_zero_returns_failure(self):
        tool = CalculatorTool()
        result = tool.execute("5 / 0")
        assert result.success is False
        assert "zero" in result.result.lower()


# ===========================================================================
# ToolRegistry
# ===========================================================================

class TestToolRegistry:
    """Test the ToolRegistry operations."""

    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = CalculatorTool()
        reg.register(tool)
        assert reg.get("calculator") is tool

    def test_get_nonexistent_returns_none(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(CalculatorTool())
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"
        assert "description" in tools[0]

    def test_duplicate_registration_raises(self):
        reg = ToolRegistry()
        reg.register(CalculatorTool())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(CalculatorTool())

    def test_list_tools_empty_registry(self):
        reg = ToolRegistry()
        assert reg.list_tools() == []


class TestGlobalRegistry:
    """Ensure the global registry has the calculator registered (via main.py)."""

    def test_calculator_in_global_registry(self):
        # The import of app.main triggers tool registration
        registry = get_registry()
        calc = registry.get("calculator")
        assert calc is not None
        assert calc.name == "calculator"


class TestCalculatorThroughRegistry:
    """Test calculator invocation through the registry lookup."""

    def test_invoke_via_registry(self):
        registry = get_registry()
        tool = registry.get("calculator")
        assert tool is not None
        result = tool.execute("125 / 5")
        assert result.success is True
        assert result.result == "25"


# ===========================================================================
# Tool Decision Service
# ===========================================================================

class TestExtractCalculatorExpression:
    """Test the expression extraction regex."""

    def test_calculate_prefix(self):
        assert _extract_calculator_expression("Calculate 25 * 4") == "25 * 4"

    def test_compute_prefix(self):
        assert _extract_calculator_expression("Compute 10 + 20") == "10 + 20"

    def test_what_is_pattern(self):
        assert _extract_calculator_expression("What is 125 * 48?") == "125 * 48"

    def test_how_much_pattern(self):
        assert _extract_calculator_expression("How much is 3 + 5?") == "3 + 5"

    def test_pure_math(self):
        assert _extract_calculator_expression("25 * 4") == "25 * 4"

    def test_non_math_returns_none(self):
        assert _extract_calculator_expression("Explain Java inheritance") is None

    def test_plain_text_returns_none(self):
        assert _extract_calculator_expression("Hello, how are you?") is None


class TestDecideTool:
    """Test the async decide_tool function."""

    @pytest.mark.asyncio
    async def test_calculator_needed(self):
        decision = await decide_tool("What is 125 * 48?")
        assert decision.tool_needed is True
        assert decision.tool_name == "calculator"
        assert decision.tool_result is not None
        assert decision.tool_result.success is True
        assert decision.tool_result.result == "6000"

    @pytest.mark.asyncio
    async def test_no_tool_for_general(self):
        decision = await decide_tool("Explain Java inheritance")
        assert decision.tool_needed is False
        assert decision.tool_name is None
        assert decision.tool_result is None

    @pytest.mark.asyncio
    async def test_no_tool_for_coding(self):
        decision = await decide_tool("Write a Python function to sort a list")
        assert decision.tool_needed is False

    @pytest.mark.asyncio
    async def test_no_tool_for_debugging(self):
        decision = await decide_tool("Fix this TypeError in my code")
        assert decision.tool_needed is False

    @pytest.mark.asyncio
    async def test_pure_math_expression(self):
        decision = await decide_tool("25 * 4")
        assert decision.tool_needed is True
        assert decision.tool_result.result == "100"


# ===========================================================================
# Integration: existing agents still work
# ===========================================================================

class TestExistingAgentsStillWork:
    """Verify Phase 3 agents are unaffected by Phase 4 changes."""

    @pytest.mark.asyncio
    async def test_coding_agent_unchanged(self):
        from app.agents.coding_agent import CodingAgent
        from app.schemas.supervisor import SupervisorDecision

        agent = CodingAgent()
        decision = SupervisorDecision(intent="coding", complexity="simple", plan=["Write code"])
        result = await agent.handle("Write a loop", decision)
        assert result.agent_name == "CodingAgent"
        assert "Coding Specialist" in result.system_prompt

    @pytest.mark.asyncio
    async def test_debugging_agent_unchanged(self):
        from app.agents.debugging_agent import DebuggingAgent
        from app.schemas.supervisor import SupervisorDecision

        agent = DebuggingAgent()
        decision = SupervisorDecision(intent="debugging", complexity="moderate", plan=["Debug"])
        result = await agent.handle("Fix this error", decision)
        assert result.agent_name == "DebuggingAgent"
        assert "Debugging Specialist" in result.system_prompt

    @pytest.mark.asyncio
    async def test_study_agent_unchanged(self):
        from app.agents.study_agent import StudyAgent
        from app.schemas.supervisor import SupervisorDecision

        agent = StudyAgent()
        decision = SupervisorDecision(intent="learning", complexity="complex", plan=["Explain"])
        result = await agent.handle("What is polymorphism?", decision)
        assert result.agent_name == "StudyAgent"
        assert "Study & Learning Specialist" in result.system_prompt


# ===========================================================================
# Integration: /api/chat still works end-to-end
# ===========================================================================

class TestChatWithToolIntegration:
    """Verify /api/chat behavior with Phase 4 tool calling."""

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_non_tool_request_works(self, mock_llm):
        """A regular coding request still flows through the normal path."""
        mock_llm.return_value = "Here is a function."

        response = client.post(
            "/api/chat",
            json={"message": "Write a function to sort a list"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Here is a function."
        assert "response" in data

    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    def test_calculator_request_enriches_prompt(self, mock_llm):
        """A calculator request appends the tool result to the user prompt."""
        mock_llm.return_value = "The result of 25 * 4 is 100."

        response = client.post(
            "/api/chat",
            json={"message": "Calculate 25 * 4"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "The result of 25 * 4 is 100."

        # Verify the prompt was enriched with tool result.
        # "Calculate 25 * 4" is general intent → get_llm_response is called
        # with the enriched message as the first positional arg.
        call_args = mock_llm.call_args
        enriched_message = call_args.args[0] if call_args.args else call_args.kwargs.get("user_message", "")
        assert "Tool Result" in enriched_message
        assert "100" in enriched_message

    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    def test_general_non_tool_request(self, mock_llm):
        """A general non-tool request still uses the fallback LLM path."""
        mock_llm.return_value = "Hello!"

        response = client.post(
            "/api/chat",
            json={"message": "Hello, how are you?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello!"

    def test_empty_message_still_returns_422(self):
        """Empty message validation is unchanged."""
        response = client.post("/api/chat", json={"message": ""})
        assert response.status_code == 422

    def test_response_format_unchanged(self):
        """The response format remains { 'response': '...' } with new HITL fields."""
        with patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test response"
            response = client.post(
                "/api/chat",
                json={"message": "Write code to print hello"},
            )
            data = response.json()
            assert "response" in data
            assert data.get("requires_approval", False) is False
