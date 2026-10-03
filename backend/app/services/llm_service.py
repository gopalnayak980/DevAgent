"""
LLM Service — handles communication with the LLM provider.

Uses the OpenAI-compatible client so the underlying provider
(OpenAI, Groq, OpenRouter, local models, etc.) can be swapped
by changing environment variables alone.
"""

from __future__ import annotations

import logging
from typing import Optional

from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, APIStatusError

from app.config import settings
from app.schemas.supervisor import SupervisorDecision

logger = logging.getLogger(__name__)

# Base system prompt — a helpful AI software engineering assistant.
SYSTEM_PROMPT = (
    "You are DevAgent, an AI software engineering assistant. "
    "You help developers with coding questions, debugging, code reviews, "
    "architecture decisions, and software engineering best practices. "
    "Provide clear, concise, and accurate answers. "
    "When sharing code, use proper formatting and include brief explanations."
)


def _build_system_prompt(supervisor_context: Optional[SupervisorDecision] = None) -> str:
    """
    Build the full system prompt.

    When a supervisor decision is provided, structured guidance is appended
    so the LLM can tailor its response strategy.
    """
    if supervisor_context is None:
        return SYSTEM_PROMPT

    plan_text = "\n".join(f"  {i + 1}. {step}" for i, step in enumerate(supervisor_context.plan))

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"--- Supervisor Guidance ---\n"
        f"Intent: {supervisor_context.intent}\n"
        f"Complexity: {supervisor_context.complexity}\n"
        f"Plan:\n{plan_text}\n"
        f"Follow the plan above to structure your response."
    )


def _get_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured from environment variables."""
    if not settings.LLM_API_KEY:
        raise ConnectionError(
            "LLM_API_KEY is not configured. "
            "Please set it in your .env file."
        )

    kwargs: dict = {
        "api_key": settings.LLM_API_KEY,
        "timeout": float(settings.LLM_TIMEOUT_SECONDS),
    }

    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL

    return AsyncOpenAI(**kwargs)


async def get_llm_response(
    user_message: str,
    supervisor_context: Optional[SupervisorDecision] = None,
) -> str:
    """
    Send the user's message to the LLM and return the assistant's reply.

    Args:
        user_message: The raw user message.
        supervisor_context: Optional supervisor decision to guide the LLM.

    Raises:
        TimeoutError: If the LLM request exceeds the configured timeout.
        ConnectionError: If the LLM service is unreachable or misconfigured.
        RuntimeError: For unexpected LLM errors.
    """
    try:
        client = _get_client()
        system_prompt = _build_system_prompt(supervisor_context)

        completion = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        # Extract the response text
        choice = completion.choices[0]
        response_text = choice.message.content

        if not response_text:
            raise RuntimeError("LLM returned an empty response.")

        return response_text.strip()

    except APITimeoutError as exc:
        logger.error("LLM API timeout: %s", exc)
        raise TimeoutError("LLM request timed out.") from exc

    except APIConnectionError as exc:
        logger.error("LLM API connection error: %s", exc)
        raise ConnectionError("Cannot connect to LLM service.") from exc

    except APIStatusError as exc:
        logger.error("LLM API status error (%s): %s", exc.status_code, exc.message)
        raise RuntimeError(f"LLM service error: {exc.status_code}") from exc

    except (TimeoutError, ConnectionError):
        # Re-raise our own mapped exceptions
        raise

    except Exception as exc:
        logger.error("Unexpected LLM error: %s", exc)
        raise RuntimeError("Unexpected error communicating with LLM.") from exc


async def get_llm_response_with_prompts(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Send explicit system and user prompts to the LLM.

    Used by Phase 3 specialized agents that construct their own
    tailored prompts. The LLM service remains the single provider
    abstraction — agents never create their own clients.

    Args:
        system_prompt: The full system prompt prepared by the agent.
        user_prompt: The user prompt (possibly enriched by the agent).

    Raises:
        TimeoutError: If the LLM request exceeds the configured timeout.
        ConnectionError: If the LLM service is unreachable or misconfigured.
        RuntimeError: For unexpected LLM errors.
    """
    try:
        client = _get_client()

        completion = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        choice = completion.choices[0]
        response_text = choice.message.content

        if not response_text:
            raise RuntimeError("LLM returned an empty response.")

        return response_text.strip()

    except APITimeoutError as exc:
        logger.error("LLM API timeout: %s", exc)
        raise TimeoutError("LLM request timed out.") from exc

    except APIConnectionError as exc:
        logger.error("LLM API connection error: %s", exc)
        raise ConnectionError("Cannot connect to LLM service.") from exc

    except APIStatusError as exc:
        logger.error("LLM API status error (%s): %s", exc.status_code, exc.message)
        raise RuntimeError(f"LLM service error: {exc.status_code}") from exc

    except (TimeoutError, ConnectionError):
        raise

    except Exception as exc:
        logger.error("Unexpected LLM error: %s", exc)
        raise RuntimeError("Unexpected error communicating with LLM.") from exc
