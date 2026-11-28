
from routing.routing_rules import make_route_decision


test_cases = [
    ("T01", "business_research", "low", "low"),
    ("T02", "analysis", "low", "medium"),
    ("T03", "planning", "medium", "medium"),
    ("T04", "recovery", "low", "high"),
    ("T05", "verification", "medium", "high"),
    ("T06", "business_research", "high", "high"),
    ("T07", "planning", "critical", "high"),
]


for task_id, category, risk, expected_model in test_cases:

    decision = make_route_decision(
        task_id=task_id,
        task_category=category,
        risk_level=risk
    )

    assert decision.selected_model == expected_model, (
        f"{task_id}: Expected {expected_model}, "
        f"got {decision.selected_model}"
    )

    print(
        f"{task_id}: {category}, {risk} risk "
        f"-> {decision.selected_model} | "
        f"Verification: {decision.requires_verification} | "
        f"Human approval: {decision.requires_human_approval}"
    )

try:
    make_route_decision(
        task_id="T08",
        task_category="unknown_task",
        risk_level="low"
    )
except ValueError as error:
    print("\nInvalid input handled correctly:")
    print(error)
else:
    raise AssertionError("Invalid category was accepted!")



try:
    make_route_decision(
        task_id="T09",
        task_category="analysis",
        risk_level="urgent"
    )
except ValueError as error:
    print("\nInvalid risk level handled correctly:")
    print(error)
else:
    raise AssertionError("Invalid risk level was accepted!")

print("\nAll routing tests passed!")
