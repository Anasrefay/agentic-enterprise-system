from pydantic import BaseModel, ConfigDict, Field
from orchestration.contracts.plan_node import PlanNode

class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    plan_id: str = Field(min_length=1)
    nodes: list[PlanNode] = Field(min_length=1)
    description: str = ""
