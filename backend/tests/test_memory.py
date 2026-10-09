import pytest
from app.database.models import Conversation, Message, Memory
from app.memory.repository import MemoryRepository
from app.memory.service import MemoryService

@pytest.mark.asyncio
async def test_memory_repository(setup_test_db):
    session = setup_test_db
    repo = MemoryRepository(session)
    
    # Test create memory
    mem = Memory(user_id="user1", memory_type="fact", content="Loves Python")
    created = await repo.create_memory(mem)
    assert created.id is not None
    
    # Test get memories
    mems = await repo.get_memories_for_user("user1")
    assert len(mems) == 1
    assert mems[0].content == "Loves Python"
    
    # Test search memories
    search = await repo.search_memories("user1", "Python programming")
    assert len(search) == 1
    search_empty = await repo.search_memories("user1", "Java")
    assert len(search_empty) == 0

@pytest.mark.asyncio
async def test_memory_service(setup_test_db):
    session = setup_test_db
    repo = MemoryRepository(session)
    service = MemoryService(repo)
    
    # Test extraction
    await service.extract_and_save_memory("user2", "I prefer JavaScript over Python.")
    mems = await repo.get_memories_for_user("user2")
    assert len(mems) == 1
    assert "JavaScript" in mems[0].content
    assert mems[0].memory_type == "preference"
    
    # Test extraction - Goal
    await service.extract_and_save_memory("user2", "My goal is to learn React.")
    mems = await repo.get_memories_for_user("user2")
    assert len(mems) == 2
    assert mems[1].memory_type == "goal"
    
    # Test formatting
    context = service.format_memory_context(mems)
    assert "[Relevant User Context]" in context
    assert "(preference)" in context
    assert "(goal)" in context
    
    # Test conversation logic — ensure_conversation now creates a unique UUID
    conv_id = await service.ensure_conversation("user2")
    assert conv_id is not None
    assert len(conv_id) > 0
    # Should NOT be the old hardcoded sentinel
    assert conv_id != "default_conv"
    await service.save_message(conv_id, "user", "Hello there")
    
    # Passing the same conv_id back should return the same ID (continuation)
    conv_id2 = await service.ensure_conversation("user2", conv_id)
    assert conv_id2 == conv_id

@pytest.mark.asyncio
async def test_memory_retrieval_with_punctuation(setup_test_db):
    """Regression test for Phase 5 memory bug where punctuation broke retrieval."""
    session = setup_test_db
    repo = MemoryRepository(session)
    service = MemoryService(repo)
    user_id = "test_user_regression"
    
    # Step 1: Save
    await service.extract_and_save_memory(user_id, "My goal is to become a full-stack developer.")
    
    # Step 2: Query
    query = "What is my main career goal?"
    
    # Step 3: Verify relevant memory is retrieved
    relevant = await service.get_relevant_memories(user_id, query)
    assert len(relevant) == 1
    assert "full-stack developer" in relevant[0].content
    
    context = service.format_memory_context(relevant)
    assert "full-stack developer" in context
