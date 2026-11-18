"""Repository container providing access to all repositories."""

from sqlalchemy.orm import Session

from app.database.repositories.user import UserRepository
from app.database.repositories.conversation import ConversationRepository, MessageRepository
from app.database.repositories.execution import ExecutionRepository
from app.database.repositories.task import TaskRepository
from app.database.repositories.memory import MemoryRepository
from app.database.repositories.mcp_server import McpServerRepository, McpAuditRepository
from app.database.repositories.approval import ApprovalRepository
from app.database.repositories.setting import SettingRepository


class Repositories:
    """Container for all repositories, sharing a single database session."""

    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.executions = ExecutionRepository(db)
        self.tasks = TaskRepository(db)
        self.memories = MemoryRepository(db)
        self.mcp_servers = McpServerRepository(db)
        self.mcp_audit = McpAuditRepository(db)
        self.approvals = ApprovalRepository(db)
        self.settings = SettingRepository(db)

