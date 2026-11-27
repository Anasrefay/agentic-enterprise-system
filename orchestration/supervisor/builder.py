from orchestration.contracts.plan import Plan
from orchestration.contracts.request import Request
from orchestration.contracts.task_state import TaskState
from orchestration.state.state_machine import load_plan
from orchestration.supervisor.planner import Planner


class PlanPolicyError(ValueError):
    """Raised when a plan violates execution safety rules."""


def check_policy(plan: Plan) -> None:
    unsafe_nodes = [
        node.node_id
        for node in plan.nodes
        if node.side_effect_class == "write" and not node.requires_approval
    ]

    if unsafe_nodes:
        raise PlanPolicyError(
            "Write nodes must require approval: "
            + ", ".join(unsafe_nodes)
        )


def build_task_state(request: Request, plan: Plan) -> TaskState:
    check_policy(plan)

    state = TaskState.new(request)
    load_plan(state, plan.nodes)

    return state


def build_refund_task(order_id: str,request: Request | None = None,planner: Planner | None = None,) -> TaskState:
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order_id cannot be empty.")

    order_id = order_id.strip()

    if planner is None:
        planner = Planner()

    plan = planner.create_refund_plan(order_id)

    if request is None:
        request = Request(goal=f"Process refund for order {order_id}")

    return build_task_state(request, plan)
