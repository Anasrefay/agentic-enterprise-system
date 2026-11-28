
import asyncio

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.step_result import StepResult
from orchestration.contracts.task_state import TaskState

from routing.routing_rules import make_route_decision
from routing.route_executor import execute_route


def get_task_category(node: PlanNode) -> str:
    category = node.params.get("task_category")

    if category:
        return category

    if node.role.lower() == "finance":
        return "analysis"

    return "business_research"


def get_risk_level(node: PlanNode) -> str:
    risk = node.params.get("risk_level")

    if risk:
        return risk

    if node.side_effect_class == "write":
        return "high"

    if node.role.lower() == "finance":
        return "medium"

    return "low"


async def model_node_runner(
    node: PlanNode,
    state: TaskState
) -> StepResult:

    task_category = get_task_category(node)
    risk_level = get_risk_level(node)

    decision = make_route_decision(
        task_id=node.node_id,
        task_category=task_category,
        risk_level=risk_level
    )

    previous_results = {
        dep: state.results[dep].output
        for dep in node.depends_on
        if dep in state.results
    }

    prompt = f"""
Task role: {node.role}

Task instruction:
{node.instruction}

Task parameters:
{node.params}

Previous results:
{previous_results}

Return a clear result for this task.
"""

    response = await asyncio.to_thread(
        execute_route,
        decision,
        prompt,
        "primary"
    )

    return StepResult.ok(
        node_id=node.node_id,
        output={
            "content": response.content,
            "model": response.resolved_model,
            "requested_model": response.requested_model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "total_tokens": response.total_tokens,
            "latency_ms": response.latency_ms,
            "cost_usd": response.cost_usd
        }
    )
