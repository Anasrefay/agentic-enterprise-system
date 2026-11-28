
from routing.route_decision import RouteDecision


VALID_CATEGORIES = {
    "business_research",
    "analysis",
    "planning",
    "risk_assessment",
    "verification",
    "recovery",
}

VALID_RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "critical",
}


def validate_inputs(task_category: str, risk_level: str) -> None:
    if task_category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown task category: {task_category}"
        )

    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            f"Unknown risk level: {risk_level}"
        )


def select_model(task_category: str, risk_level: str) -> str:
    validate_inputs(task_category, risk_level)

    if risk_level in ["high", "critical"]:
        return "high"

    if task_category in ["verification", "recovery"]:
        return "high"

    if risk_level == "medium":
        return "medium"

    if task_category in ["analysis", "planning"]:
        return "medium"

    return "low"


def make_route_decision(
    task_id: str,
    task_category: str,
    risk_level: str
) -> RouteDecision:

    selected_model = select_model(task_category, risk_level)

    requires_verification = (
        risk_level in ["high", "critical"]
        or task_category in ["verification", "recovery"]
    )

    requires_human_approval = risk_level == "critical"

    reason = (
        f"Selected {selected_model} model based on "
        f"task category '{task_category}' and "
        f"risk level '{risk_level}'."
    )

    if requires_human_approval:
        reason += " Human approval is required before execution."

    return RouteDecision(
        task_id=task_id,
        task_category=task_category,
        risk_level=risk_level,
        selected_model=selected_model,
        requires_verification=requires_verification,
        requires_human_approval=requires_human_approval,
        reason=reason
    )
