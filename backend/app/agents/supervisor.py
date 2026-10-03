"""
Supervisor Agent — Phase 2.

Analyzes the user's message to classify intent, estimate complexity,
and produce a structured plan before delegating to the LLM service.

This module is entirely deterministic (keyword-based classification).
No LLM call is made by the supervisor itself — the existing LLM service
remains the single LLM provider abstraction.
"""

import logging
import re

from app.schemas.supervisor import SupervisorDecision

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword sets used for deterministic intent classification
# ---------------------------------------------------------------------------

_DEBUGGING_KEYWORDS: set[str] = {
    "bug", "error", "exception", "traceback", "fix", "crash", "issue",
    "debug", "debugging", "broken", "failing", "failure", "fault",
    "not working", "stack trace", "segfault", "undefined", "null",
    "typeerror", "valueerror", "keyerror", "attributeerror", "syntaxerror",
    "indexerror", "importerror", "nameerror", "runtimeerror",
    "referenceerror", "assertion", "unexpected",
}

_CODING_KEYWORDS: set[str] = {
    "code", "function", "class", "implement", "write", "create",
    "build", "develop", "program", "script", "algorithm", "api",
    "endpoint", "module", "library", "package", "method", "refactor",
    "optimize", "generate", "component", "template", "boilerplate",
    "snippet", "helper", "utility", "factory", "handler", "middleware",
    "decorator", "async", "await", "lambda", "constructor",
}

_LEARNING_KEYWORDS: set[str] = {
    "explain", "what is", "how does", "why does", "learn", "understand",
    "concept", "tutorial", "difference between", "compare", "meaning",
    "definition", "overview", "introduction", "basics", "fundamentals",
    "best practice", "best practices", "pros and cons", "advantages",
    "disadvantages", "when to use", "how to use", "example",
    "examples", "guide", "walkthrough",
}

# ---------------------------------------------------------------------------
# Complexity heuristics
# ---------------------------------------------------------------------------

_COMPLEX_SIGNALS: list[str] = [
    "architecture", "design pattern", "system design", "migrate",
    "migration", "microservice", "distributed", "scale", "scalability",
    "security", "authentication", "authorization", "deployment",
    "infrastructure", "database schema", "data model",
]

_MODERATE_SIGNALS: list[str] = [
    "multiple", "integrate", "connect", "combine", "several",
    "test", "testing", "validate", "configuration", "setup",
    "workflow", "pipeline", "ci", "cd",
]


def _normalise(text: str) -> str:
    """Lower-case and collapse whitespace for keyword matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _classify_intent(text: str) -> str:
    """Return one of: debugging, coding, learning, general."""
    normalised = _normalise(text)

    # Debugging takes priority — a user who says "fix this code" is debugging.
    for kw in _DEBUGGING_KEYWORDS:
        if kw in normalised:
            return "debugging"

    for kw in _CODING_KEYWORDS:
        if kw in normalised:
            return "coding"

    for kw in _LEARNING_KEYWORDS:
        if kw in normalised:
            return "learning"

    return "general"


def _estimate_complexity(text: str) -> str:
    """Return one of: simple, moderate, complex."""
    normalised = _normalise(text)
    word_count = len(normalised.split())

    for signal in _COMPLEX_SIGNALS:
        if signal in normalised:
            return "complex"

    for signal in _MODERATE_SIGNALS:
        if signal in normalised:
            return "moderate"

    # Long messages are likely more involved.
    if word_count > 80:
        return "complex"
    if word_count > 30:
        return "moderate"

    return "simple"


# ---------------------------------------------------------------------------
# Plan templates keyed by (intent, complexity)
# ---------------------------------------------------------------------------

_PLAN_TEMPLATES: dict[tuple[str, str], list[str]] = {
    # Coding
    ("coding", "simple"): [
        "Understand the user's coding request",
        "Generate a technically correct solution with clear formatting",
    ],
    ("coding", "moderate"): [
        "Understand the user's coding request",
        "Break the problem into logical steps",
        "Generate a well-structured solution with explanations",
        "Highlight any edge cases or caveats",
    ],
    ("coding", "complex"): [
        "Understand the user's coding request and constraints",
        "Outline a high-level approach before implementation",
        "Break the solution into modular components",
        "Generate a complete, well-documented solution",
        "Discuss trade-offs, alternatives, and potential improvements",
    ],
    # Debugging
    ("debugging", "simple"): [
        "Identify the error or issue described by the user",
        "Explain the root cause clearly",
        "Provide the corrected code or fix",
    ],
    ("debugging", "moderate"): [
        "Identify the error or issue described by the user",
        "Analyze potential root causes",
        "Suggest a systematic debugging approach",
        "Provide the fix with a clear explanation",
    ],
    ("debugging", "complex"): [
        "Identify the error or issue described by the user",
        "Analyze the broader context that may contribute to the problem",
        "Consider multiple potential root causes",
        "Provide a step-by-step debugging strategy",
        "Provide the fix and recommend preventive measures",
    ],
    # Learning
    ("learning", "simple"): [
        "Identify the concept the user wants to learn about",
        "Provide a clear, concise explanation with examples",
    ],
    ("learning", "moderate"): [
        "Identify the concept or topic the user wants to understand",
        "Provide a structured explanation with relevant examples",
        "Compare with related concepts if applicable",
    ],
    ("learning", "complex"): [
        "Identify the topic the user wants to understand in depth",
        "Provide a comprehensive explanation with context",
        "Include practical examples and real-world use cases",
        "Discuss trade-offs, best practices, and further resources",
    ],
    # General
    ("general", "simple"): [
        "Understand the user's request",
        "Provide a helpful and accurate response",
    ],
    ("general", "moderate"): [
        "Understand the user's request and context",
        "Provide a detailed and well-organized response",
        "Include relevant examples or references",
    ],
    ("general", "complex"): [
        "Understand the user's request and full context",
        "Provide a thorough, well-structured response",
        "Include examples, comparisons, and actionable recommendations",
        "Highlight nuances and important considerations",
    ],
}


def _build_plan(intent: str, complexity: str) -> list[str]:
    """Return a plan based on the classified intent and complexity."""
    return _PLAN_TEMPLATES.get(
        (intent, complexity),
        _PLAN_TEMPLATES[("general", "simple")],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze(user_message: str) -> SupervisorDecision:
    """
    Analyze a user message and produce a structured supervisor decision.

    This is a deterministic, keyword-based analysis — fast and predictable.
    No external calls are made.

    Args:
        user_message: The raw message from the user.

    Returns:
        A SupervisorDecision with intent, complexity, and plan.

    Raises:
        ValueError: If the message is empty.
    """
    if not user_message or not user_message.strip():
        raise ValueError("Cannot analyze an empty message.")

    intent = _classify_intent(user_message)
    complexity = _estimate_complexity(user_message)
    plan = _build_plan(intent, complexity)

    decision = SupervisorDecision(
        intent=intent,
        complexity=complexity,
        plan=plan,
    )

    logger.info(
        "Supervisor decision — intent=%s, complexity=%s, plan_steps=%d",
        decision.intent,
        decision.complexity,
        len(decision.plan),
    )

    return decision
