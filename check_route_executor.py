
from routing.routing_rules import make_route_decision
from routing.route_executor import execute_route


# TEST 1: Execute a real model call

print("=" * 45)
print("TEST 1: MODEL EXECUTION")
print("=" * 45)

decision = make_route_decision(
    task_id="TEST01",
    task_category="business_research",
    risk_level="low"
)

print("Selected model:", decision.selected_model)

response = execute_route(
    decision=decision,
    prompt="In one sentence, explain what a business plan is.",
    call_role="primary"
)

print("\nMODEL RESPONSE:")
print(response.content)

print("\nMODEL INFORMATION:")
print("Requested:", response.requested_model)
print("Resolved:", response.resolved_model)
print("Latency:", response.latency_ms, "ms")
print("Total tokens:", response.total_tokens)

print("\nModel execution test passed!")


# TEST 2: Critical task approval requirement

print("\n" + "=" * 45)
print("TEST 2: HUMAN APPROVAL REQUIREMENT")
print("=" * 45)

critical_decision = make_route_decision(
    task_id="TEST02",
    task_category="planning",
    risk_level="critical"
)

print("Selected model:", critical_decision.selected_model)
print("Human approval required:",
      critical_decision.requires_human_approval)

assert critical_decision.requires_human_approval is True, (
    "Critical task must require human approval!"
)

print("\nCritical task approval requirement test passed!")
