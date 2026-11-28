from dataclasses import dataclass
from typing import Optional


@dataclass
class RouteDecision:
    task_id: str
    task_category: str
    risk_level: str

    selected_model: Optional[str]

    requires_verification: bool
    requires_human_approval: bool

    reason: str
    policy_version: str = "1.0"