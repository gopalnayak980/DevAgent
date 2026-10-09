import re
from typing import List, Optional
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
                
    async def ensure_conversation(self, user_id: str, conv_id: Optional[str] = None) -> str:
        """Ensure a conversation exists for the user. Return the conversation ID."""
        if conv_id:
            conv = await self.repository.get_conversation(conv_id)
            if not conv or conv.user_id != user_id:
                raise ValueError("Conversation not found or access denied")
            return conv.id
        else:
            import uuid
            new_id = str(uuid.uuid4())
            conv = Conversation(id=new_id, user_id=user_id)
            await self.repository.create_conversation(conv)
            return conv.id
        
    async def save_message(self, conv_id: str, role: str, content: str) -> None:
        """Save a message to the conversation history."""
        msg = Message(conversation_id=conv_id, role=role, content=content)
        await self.repository.create_message(msg)

    async def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """Get all conversations for a user, sorted by updated_at descending."""
        return await self.repository.get_conversations_for_user(user_id)

    async def get_conversation_messages(self, user_id: str, conv_id: str) -> List[Message]:
        """Get messages for a conversation, verifying ownership first."""
        conv = await self.repository.get_conversation(conv_id)
        if not conv or conv.user_id != user_id:
            raise ValueError("Conversation not found or access denied")
        return await self.repository.get_messages_for_conversation(conv_id)
