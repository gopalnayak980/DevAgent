"""
Tests for the Supervisor Agent — Phase 2.

Covers:
- Intent classification (coding, debugging, learning, general)
- Complexity estimation (simple, moderate, complex)
- Plan generation
- Edge cases (empty message)
"""

import pytest

from app.agents.supervisor import analyze, _classify_intent, _estimate_complexity


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

class TestClassifyIntent:
    """Tests for _classify_intent (deterministic keyword matching)."""

    @pytest.mark.parametrize(
        "message, expected",
        [
            ("Write a Python function to sort a list", "coding"),
            ("Create a REST API endpoint", "coding"),
            ("Implement a binary search algorithm", "coding"),
            ("Build a React component for a form", "coding"),
            ("Refactor this class to use dependency injection", "coding"),
        ],
    )
    def test_coding_intent(self, message: str, expected: str):
        assert _classify_intent(message) == expected

    @pytest.mark.parametrize(
        "message, expected",
        [
            ("Fix this TypeError in my code", "debugging"),
            ("I'm getting a null pointer exception", "debugging"),
            ("Why is my application crashing on startup?", "debugging"),
            ("Debug this failing test", "debugging"),
            ("There's a bug in my login flow", "debugging"),
            ("I see a traceback when running the server", "debugging"),
        ],
    )
    def test_debugging_intent(self, message: str, expected: str):
        assert _classify_intent(message) == expected

    @pytest.mark.parametrize(
        "message, expected",
        [
            ("Explain how HTTP request-response cycle works", "learning"),
            ("What is the difference between REST and GraphQL?", "learning"),
            ("Give me a tutorial on Docker basics", "learning"),
            ("What are the best practices for naming variables?", "learning"),
            ("How does garbage collection work in Java?", "learning"),
        ],
    )
    def test_learning_intent(self, message: str, expected: str):
        assert _classify_intent(message) == expected

    @pytest.mark.parametrize(
        "message, expected",
        [
            ("Hello", "general"),
            ("Thanks for the help!", "general"),
            ("What time is it?", "general"),
            ("Tell me a joke", "general"),
        ],
    )
    def test_general_intent(self, message: str, expected: str):
        assert _classify_intent(message) == expected


# ---------------------------------------------------------------------------
# Complexity estimation
# ---------------------------------------------------------------------------

class TestEstimateComplexity:
    """Tests for _estimate_complexity."""

    def test_simple_short_message(self):
        assert _estimate_complexity("Write a hello world program") == "simple"

    def test_moderate_with_keyword(self):
        assert _estimate_complexity("How do I integrate multiple services?") == "moderate"

    def test_complex_with_keyword(self):
        assert _estimate_complexity("Design a microservice architecture for e-commerce") == "complex"

    def test_long_message_is_moderate(self):
        # A message with more than 30 words triggers moderate
        message = " ".join(["word"] * 35)
        assert _estimate_complexity(message) == "moderate"

    def test_very_long_message_is_complex(self):
        # A message with more than 80 words triggers complex
        message = " ".join(["word"] * 85)
        assert _estimate_complexity(message) == "complex"


# ---------------------------------------------------------------------------
# Full analyze() function
# ---------------------------------------------------------------------------

class TestAnalyze:
    """Tests for the public analyze() function."""

    @pytest.mark.asyncio
    async def test_analyze_coding_simple(self):
        decision = await analyze("Write a Python function to add two numbers")
        assert decision.intent == "coding"
        assert decision.complexity == "simple"
        assert len(decision.plan) >= 2
        assert all(isinstance(step, str) for step in decision.plan)

    @pytest.mark.asyncio
    async def test_analyze_debugging(self):
        decision = await analyze("I'm getting an error when I run my Flask app")
        assert decision.intent == "debugging"
        assert len(decision.plan) >= 2

    @pytest.mark.asyncio
    async def test_analyze_learning(self):
        decision = await analyze("Explain what is polymorphism in Java")
        assert decision.intent == "learning"
        assert len(decision.plan) >= 2

    @pytest.mark.asyncio
    async def test_analyze_general(self):
        decision = await analyze("Hello, how are you?")
        assert decision.intent == "general"
        assert len(decision.plan) >= 2

    @pytest.mark.asyncio
    async def test_analyze_empty_message_raises(self):
        with pytest.raises(ValueError, match="empty"):
            await analyze("")

    @pytest.mark.asyncio
    async def test_analyze_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            await analyze("   ")

    @pytest.mark.asyncio
    async def test_analyze_returns_valid_pydantic_model(self):
        decision = await analyze("Create a REST API with FastAPI")
        # Verify it's a proper Pydantic model with the expected fields
        data = decision.model_dump()
        assert "intent" in data
        assert "complexity" in data
        assert "plan" in data
        assert data["intent"] in {"coding", "debugging", "learning", "general"}
        assert data["complexity"] in {"simple", "moderate", "complex"}

    @pytest.mark.asyncio
    async def test_debugging_takes_priority_over_coding(self):
        """When a message contains both debugging and coding keywords, debugging wins."""
        decision = await analyze("Fix this broken function that I wrote")
        assert decision.intent == "debugging"
