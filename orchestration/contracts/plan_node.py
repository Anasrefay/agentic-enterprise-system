from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from orchestration.contracts.request import SCHEMA_VERSION

class PlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    schema_version: str = SCHEMA_VERSION
    node_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    role: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)
    depends_on: tuple[str, ...] = ()
    input_refs: list[str] = Field(default_factory=list)
    output_schema: dict[str, Any]
    preconditions: list[str] = Field(default_factory=list)
    side_effect_class: Literal["read", "write", "none"]
    requires_approval: bool = False
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> "PlanNode":
        if self.node_id in self.depends_on:
            raise ValueError(f"node '{self.node_id}' depends on itself")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"node '{self.node_id}' has duplicate dependencies")
        return self
