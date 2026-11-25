"""StepResult contract: what a node returns after execution.

`facts` is the section M3 reviews: every claim must carry a source and a
confidence in [0, 1].
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orchestration.contracts.request import SCHEMA_VERSION, utcnow


class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"    # error: eligible for retry
    BLOCKED = "blocked"  # cannot proceed (missing input, policy...): no retry


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    claim: str = Field(min_length=1)
    source: str = Field(min_length=1)  # url / doc id / node id
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str | None = None


class StepResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    node_id: str
    status: StepStatus
    output: dict[str, Any] = Field(default_factory=dict)
    facts: tuple[Fact, ...] = ()
    reason: str | None = None  # mandatory when not SUCCESS
    attempt: int = Field(default=1, ge=1)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _check(self) -> "StepResult":
        if self.status is StepStatus.SUCCESS:
            if self.reason:
                raise ValueError("a successful result must not carry a reason")
        elif not (self.reason and self.reason.strip()):
            raise ValueError(f"a {self.status.value} result requires an explicit reason")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at is earlier than started_at")
        return self

    # --- convenience constructors (handy for stub nodes) ---
    @classmethod
    def ok(cls, node_id: str, output: dict[str, Any] | None = None,
           facts: tuple[Fact, ...] = (), **kw: Any) -> "StepResult":
        return cls(node_id=node_id, status=StepStatus.SUCCESS,
                   output=output or {}, facts=facts, **kw)

    @classmethod
    def failed(cls, node_id: str, reason: str, **kw: Any) -> "StepResult":
        return cls(node_id=node_id, status=StepStatus.FAILED, reason=reason, **kw)

    @classmethod
    def blocked(cls, node_id: str, reason: str, **kw: Any) -> "StepResult":
        return cls(node_id=node_id, status=StepStatus.BLOCKED, reason=reason, **kw)
