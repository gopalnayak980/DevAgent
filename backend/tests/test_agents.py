"""
Tests for Phase 3 Specialized Agents.
"""

import pytest
from app.schemas.supervisor import SupervisorDecision
from app.agents.coding_agent import CodingAgent
from app.agents.debugging_agent import DebuggingAgent
from app.agents.study_agent import StudyAgent
from app.agents.router import get_agent_for_intent


@pytest.mark.asyncio
async def test_coding_agent():
    agent = CodingAgent()
    decision = SupervisorDecision(intent="coding", complexity="simple", plan=["Step 1", "Step 2"])
    result = await agent.handle("Write a loop", decision)
    
    assert result.agent_name == "CodingAgent"
    assert result.user_prompt == "Write a loop"
    assert "You are DevAgent's Coding Specialist" in result.system_prompt
    assert "Step 1" in result.system_prompt
    assert "Step 2" in result.system_prompt


@pytest.mark.asyncio
async def test_debugging_agent():
    agent = DebuggingAgent()
    decision = SupervisorDecision(intent="debugging", complexity="moderate", plan=["Step A"])
    result = await agent.handle("Fix this error", decision)
    
    assert result.agent_name == "DebuggingAgent"
    assert "Debugging Specialist" in result.system_prompt
    assert "Step A" in result.system_prompt


@pytest.mark.asyncio
async def test_study_agent():
    agent = StudyAgent()
    decision = SupervisorDecision(intent="learning", complexity="complex", plan=["Explain A"])
    result = await agent.handle("What is a class?", decision)
    
    assert result.agent_name == "StudyAgent"
    assert "Study & Learning Specialist" in result.system_prompt
    assert "Explain A" in result.system_prompt


def test_router():
    assert isinstance(get_agent_for_intent("coding"), CodingAgent)
    assert isinstance(get_agent_for_intent("debugging"), DebuggingAgent)
    assert isinstance(get_agent_for_intent("learning"), StudyAgent)
    assert get_agent_for_intent("general") is None
