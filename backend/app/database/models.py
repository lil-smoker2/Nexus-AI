"""SQLAlchemy models for NEXUS AI backend."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def guid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=guid)
    username = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=guid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="settings")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=guid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=guid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=guid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True, index=True)
    agent_id = Column(String, nullable=False, index=True)  # companion / coding / computer / life_management
    user_objective = Column(Text, nullable=False)
    plan_version = Column(Integer, default=0, nullable=False)
    current_task = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending / running / completed / blocked / failed
    completed_tasks = Column(JSON, nullable=True, default=list)
    pending_tasks = Column(JSON, nullable=True, default=list)
    tool_calls = Column(JSON, nullable=True, default=list)
    tool_results = Column(JSON, nullable=True, default=list)
    errors = Column(JSON, nullable=True, default=list)
    checkpoints = Column(JSON, nullable=True, default=list)
    approvals = Column(JSON, nullable=True, default=list)
    verification_evidence = Column(JSON, nullable=True, default=list)
    final_report = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="executions")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=guid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=True, index=True)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending / in_progress / completed / blocked / failed
    required_tools = Column(JSON, nullable=True, default=list)
    completion_conditions = Column(JSON, nullable=True, default=list)
    risks = Column(JSON, nullable=True, default=list)
    dependencies = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Task", remote_side=[id], backref="subtasks")
    execution = relationship("Execution", backref="tasks")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=guid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # personal_info / preferences / interests / goals / events / projects / commitments
    content = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    embedding = Column(JSON, nullable=True)  # optional vector for semantic search
    importance = Column(Integer, nullable=True, default=5)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="memories")


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(String, primary_key=True, default=guid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    transport = Column(String, nullable=False)  # internal / stdio / streamable_http
    endpoint = Column(String, nullable=False)
    args = Column(JSON, nullable=True, default=list)
    env = Column(JSON, nullable=True, default=dict)
    auth_config = Column(JSON, nullable=True, default=dict)
    config = Column(JSON, nullable=True, default=dict)  # extra: cwd, headers, timeout, allowlisted tools, etc.
    enabled = Column(Boolean, nullable=False, default=True)
    connection_state = Column(String, nullable=False, default="disconnected")  # connected / disconnected / error
    discovered_tools = Column(JSON, nullable=True, default=list)
    permissions = Column(JSON, nullable=True, default=dict)
    server_info = Column(JSON, nullable=True, default=dict)
    capabilities = Column(JSON, nullable=True, default=dict)
    last_error = Column(Text, nullable=True)
    last_connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=guid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=True, index=True)
    tool_id = Column(String, nullable=True)
    resource = Column(String, nullable=True)
    decision = Column(String, nullable=False, default="requested")  # requested / granted / denied
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="approvals")


class McpAuditEvent(Base):
    __tablename__ = "mcp_audit_events"

    id = Column(String, primary_key=True, default=guid)
    server_id = Column(String, nullable=True, index=True)
    server_name = Column(String, nullable=True)
    tool_name = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, default="tool_call")  # tool_call/connect/disconnect/discover/error
    success = Column(Boolean, nullable=False, default=False)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
