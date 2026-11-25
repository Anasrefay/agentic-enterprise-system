"""TaskState contract: the single mutable object that flows through the system.

Mutate it ONLY through orchestration.state.state_machine so every change is
validated and recorded in `history`.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.request import SCHEMA_VERSION, Request, utcnow
from orchestration.contracts.step_result import StepResult


class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"  # terminal
    BLOCKED = "blocked"      # terminal (needs reason)
    FAILED = "failed"        # terminal (needs reason)
    CANCELLED = "cancelled"  # terminal


class NodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"  # terminal
    FAILED = "failed"        # terminal (needs reason)
    BLOCKED = "blocked"      # terminal (needs reason)


TERMINAL_TASK = frozenset({TaskStatus.COMPLETED, TaskStatus.BLOCKED,
                           TaskStatus.FAILED, TaskStatus.CANCELLED})
TERMINAL_NODE = frozenset({NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.BLOCKED})


class TransitionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope: Literal["task", "node"]
    target_id: str | None  # node_id for scope="node", else None
    from_status: str
    to_status: str
    reason: str | None = None
    at: datetime = Field(default_factory=utcnow)


class TaskState(BaseModel):
    schema_version: str = SCHEMA_VERSION
    request: Request
    status: TaskStatus = TaskStatus.CREATED
    reason: str | None = None  # explicit reason for BLOCKED / FAILED / CANCELLED
    nodes: dict[str, PlanNode] = Field(default_factory=dict)
    node_status: dict[str, NodeStatus] = Field(default_factory=dict)
    node_reasons: dict[str, str] = Field(default_factory=dict)
    results: dict[str, StepResult] = Field(default_factory=dict)
    attempts: dict[str, int] = Field(default_factory=dict)
    approvals: dict[str, bool] = Field(default_factory=dict)  # node_id -> approved?
    history: list[TransitionRecord] = Field(default_factory=list)

    @classmethod
    def new(cls, request: Request) -> "TaskState":
        return cls(request=request)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_TASK
