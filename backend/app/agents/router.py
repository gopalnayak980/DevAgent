"""
Agent Router — Phase 3.

Maps the supervisor's intent classification to the appropriate
specialized agent. Returns None for intents that don't have a
dedicated agent (e.g. "general"), so the chat route can fall back
to the existing Phase 2 behavior.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base import BaseAgent
from app.agents.coding_agent import CodingAgent
from app.agents.debugging_agent import DebuggingAgent
from app.agents.study_agent import StudyAgent

logger = logging.getLogger(__name__)

# Singleton agent instances — agents are stateless so one instance each is fine.
_AGENTS: dict[str, BaseAgent] = {
    "coding": CodingAgent(),
    "debugging": DebuggingAgent(),
    "learning": StudyAgent(),
}


def get_agent_for_intent(intent: str) -> Optional[BaseAgent]:
    """Return the specialized agent for the given intent, or None for general.

    Args:
        intent: The classified intent from the supervisor (coding, debugging,
                learning, or general).

    Returns:
        A BaseAgent instance, or None if no specialized agent is mapped.
    """
    agent = _AGENTS.get(intent)
    if agent:
        logger.info("Routing to %s for intent '%s'", agent.name, intent)
    else:
        logger.info("No specialized agent for intent '%s' — using general flow", intent)
    return agent
