"""Agent progress tracking for real-time UI updates."""

from enum import Enum
from typing import Callable, Optional
from dataclasses import dataclass
import threading


class AgentType(str, Enum):
    """Types of agents in the workflow."""

    INPUT_PARSER = "input_parser"
    INFORMATION_COLLECTOR = "information_collector"
    COMPLIANCE_CHECKER = "compliance_checker"
    CODE_GENERATOR = "code_generator"
    CODE_REVIEWER = "code_reviewer"


# Human-readable agent names for UI
AGENT_DISPLAY_NAMES = {
    AgentType.INPUT_PARSER: "解析输入",
    AgentType.INFORMATION_COLLECTOR: "收集信息",
    AgentType.COMPLIANCE_CHECKER: "合规检查",
    AgentType.CODE_GENERATOR: "生成代码",
    AgentType.CODE_REVIEWER: "代码审查",
}

# Agent descriptions for more detail
AGENT_DESCRIPTIONS = {
    AgentType.INPUT_PARSER: "正在分析您的需求...",
    AgentType.INFORMATION_COLLECTOR: "正在收集资源信息...",
    AgentType.COMPLIANCE_CHECKER: "正在检查安全策略合规性...",
    AgentType.CODE_GENERATOR: "正在生成 Terraform 代码...",
    AgentType.CODE_REVIEWER: "正在审查生成的代码...",
}


@dataclass
class ProgressEvent:
    """Progress event data."""

    agent: AgentType
    status: str  # "started", "completed", "failed"
    message: Optional[str] = None
    progress_pct: Optional[int] = None  # 0-100

    def to_dict(self) -> dict:
        return {
            "agent": self.agent.value,
            "agent_name": AGENT_DISPLAY_NAMES.get(self.agent, self.agent.value),
            "agent_description": AGENT_DESCRIPTIONS.get(self.agent, ""),
            "status": self.status,
            "message": self.message,
            "progress_pct": self.progress_pct,
        }


class ProgressTracker:
    """
    Thread-safe progress tracker for agent workflow.

    Used to send real-time progress updates to the frontend via SSE.
    """

    # Thread-local storage for session-specific callbacks
    _callbacks: dict[str, Callable[[ProgressEvent], None]] = {}
    _lock = threading.Lock()

    @classmethod
    def register_callback(
        cls, session_id: str, callback: Callable[[ProgressEvent], None]
    ):
        """Register a progress callback for a session."""
        with cls._lock:
            cls._callbacks[session_id] = callback

    @classmethod
    def unregister_callback(cls, session_id: str):
        """Unregister a progress callback for a session."""
        with cls._lock:
            cls._callbacks.pop(session_id, None)

    @classmethod
    def emit(cls, session_id: str, event: ProgressEvent):
        """Emit a progress event to the registered callback."""
        with cls._lock:
            callback = cls._callbacks.get(session_id)

        if callback:
            try:
                callback(event)
            except Exception as e:
                print(f"[ProgressTracker] Error in callback: {e}")

    @classmethod
    def agent_started(
        cls, session_id: str, agent: AgentType, message: Optional[str] = None
    ):
        """Emit agent started event."""
        cls.emit(
            session_id,
            ProgressEvent(
                agent=agent,
                status="started",
                message=message or AGENT_DESCRIPTIONS.get(agent, ""),
            ),
        )

    @classmethod
    def agent_completed(
        cls, session_id: str, agent: AgentType, message: Optional[str] = None
    ):
        """Emit agent completed event."""
        cls.emit(
            session_id,
            ProgressEvent(
                agent=agent,
                status="completed",
                message=message,
            ),
        )

    @classmethod
    def agent_failed(
        cls, session_id: str, agent: AgentType, message: Optional[str] = None
    ):
        """Emit agent failed event."""
        cls.emit(
            session_id,
            ProgressEvent(
                agent=agent,
                status="failed",
                message=message,
            ),
        )
