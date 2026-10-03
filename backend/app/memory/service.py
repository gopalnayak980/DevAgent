import re
from typing import List
from app.memory.repository import MemoryRepository
from app.database.models import Memory, Conversation, Message

class MemoryService:
    def __init__(self, repository: MemoryRepository):
        self.repository = repository
        
    async def get_relevant_memories(self, user_id: str, message: str) -> List[Memory]:
        """Retrieve relevant memories for a user message."""
        memories = await self.repository.search_memories(user_id, message)
        # Limit to top 5 memories
        return memories[:5]
        
    def format_memory_context(self, memories: List[Memory]) -> str:
        """Format memories into a string for the LLM prompt."""
        if not memories:
            return ""
        
        context_lines = ["\n[Relevant User Context]"]
        for m in memories:
            context_lines.append(f"- ({m.memory_type}) {m.content}")
        
        return "\n".join(context_lines)
        
    async def extract_and_save_memory(self, user_id: str, message: str) -> None:
        """Lightweight memory extraction. Detect explicit statements."""
        # Simple regex for phase 5
        patterns = [
            (r"I prefer\s+(.*)", "preference"),
            (r"My goal is\s+(.*)", "goal"),
            (r"I am learning\s+(.*)", "context"),
            (r"I use\s+(.*)", "context"),
            (r"I want to\s+(.*)", "goal")
        ]
        
        for pattern, m_type in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                content = f"User explicitly stated: {match.group(0)}"
                new_memory = Memory(user_id=user_id, memory_type=m_type, content=content)
                await self.repository.create_memory(new_memory)
                break # Only extract one per message for simplicity
                
    async def ensure_conversation(self, user_id: str, conv_id: str = "default_conv") -> str:
        """Ensure a conversation exists for the user. Return the conversation ID."""
        conv = await self.repository.get_conversation(conv_id)
        if not conv:
            conv = Conversation(id=conv_id, user_id=user_id)
            await self.repository.create_conversation(conv)
        return conv.id
        
    async def save_message(self, conv_id: str, role: str, content: str) -> None:
        """Save a message to the conversation history."""
        msg = Message(conversation_id=conv_id, role=role, content=content)
        await self.repository.create_message(msg)
