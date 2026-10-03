from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, delete, update
from app.database.models import Memory, Conversation, Message
from typing import List, Optional

class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_memory(self, memory: Memory) -> Memory:
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def get_memories_for_user(self, user_id: str) -> List[Memory]:
        result = await self.session.execute(select(Memory).where(Memory.user_id == user_id))
        return list(result.scalars().all())
    
    async def search_memories(self, user_id: str, query: str) -> List[Memory]:
        import re
        # Simple keyword matching for Phase 5
        # Strip punctuation to ensure words like 'goal?' match 'goal'
        clean_query = re.sub(r'[^\w\s]', '', query.lower())
        keywords = [word for word in clean_query.split() if len(word) > 3]
        if not keywords:
            return []
            
        conditions = [Memory.content.ilike(f"%{kw}%") for kw in keywords]
        stmt = select(Memory).where(Memory.user_id == user_id).where(or_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_memory(self, memory_id: str):
        stmt = delete(Memory).where(Memory.id == memory_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def create_conversation(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def create_message(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message
        
    async def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        result = await self.session.execute(select(Conversation).where(Conversation.id == conv_id))
        return result.scalar_one_or_none()
