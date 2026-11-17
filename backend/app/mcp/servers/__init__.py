"""Domain MCP server implementations."""
from .filesystem import FilesystemMcpServer
from .terminal import TerminalMcpServer
from .browser import BrowserMcpServer
from .database import DatabaseMcpServer
from .git import GitMcpServer
from .computer import ComputerAutomationMcpServer
from .task_memory import TaskMemoryMcpServer

SERVER_CLASSES = {
    "filesystem": FilesystemMcpServer,
    "terminal": TerminalMcpServer,
    "browser": BrowserMcpServer,
    "database": DatabaseMcpServer,
    "git": GitMcpServer,
    "computer": ComputerAutomationMcpServer,
    "task_memory": TaskMemoryMcpServer,
}
