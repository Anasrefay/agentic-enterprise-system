"""PlanNode contract (DRAFT by Person 1 so the scheduler can compile).

Owner: Person 2. Person 1 only relies on: node_id, depends_on, requires_approval.
`requires_approval` is the field M5 reviews.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orchestration.contracts.request import SCHEMA_VERSION


class PlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    schema_version: str = SCHEMA_VERSION
    node_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    agent: str = Field(min_length=1)          # which specialist runs it
    instruction: str = Field(min_length=1)
    depends_on: tuple[str, ...] = ()
    requires_approval: bool = False
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> "PlanNode":
        if self.node_id in self.depends_on:
            raise ValueError(f"node '{self.node_id}' depends on itself")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"node '{self.node_id}' has duplicate dependencies")
        return self
