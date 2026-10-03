from pydantic import BaseModel
from datetime import datetime

class MemoryCreate(BaseModel):
    user_id: str
    memory_type: str
    content: str
    importance: int = 1

class MemoryResponse(MemoryCreate):
    id: str
    created_at: datetime
    updated_at: datetime
