import uuid
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Phase 10.2 — Authenticated user account."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)  # 'user' | 'admin'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApprovalRequest(Base):
    """Phase 6 — Human-in-the-Loop approval request."""
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String)  # e.g. 'demo_protected_action'
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, approved, rejected, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Memory(Base):
    __tablename__ = "memories"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    memory_type: Mapped[str] = mapped_column(String) # 'preference', 'fact', 'goal', 'context'
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Job(Base):
    """Phase 7 — Background agent job."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    job_type: Mapped[str] = mapped_column(String, default="agent_task")
    input: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExecutionTrace(Base):
    """Phase 8 — Execution trace for observability and evaluation."""
    __tablename__ = "execution_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    user_id: Mapped[str] = mapped_column(String, index=True)
    task_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    complexity: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    agent_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    llm_call_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    tools_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def get_tools_used(self) -> list[str]:
        """Deserialize tools_used JSON string to a list."""
        if not self.tools_used:
            return []
        try:
            return json.loads(self.tools_used)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tools_used(self, tools: list[str]) -> None:
        """Serialize a list of tool names to JSON string."""
        self.tools_used = json.dumps(tools)

