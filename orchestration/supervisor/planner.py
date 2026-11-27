from orchestration.contracts.plan import Plan
from orchestration.contracts.plan_node import PlanNode


class Planner:

    def create_refund_plan(self, order_id: str) -> Plan:
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("order_id cannot be empty.")

        order_id = order_id.strip()

        node1 = PlanNode(
            node_id="check_eligibility",
            role="Support",
            instruction="Check if the order is eligible for a refund.",
            allowed_tools=["get_order", "check_return_policy"],
            depends_on=(),
            input_refs=["order_id"],
            output_schema={
                "type": "object",
                "properties": {
                    "eligible": {"type": "boolean"},
                    "reason": {"type": "string"}
                },
                "required": ["eligible", "reason"]
            },
            preconditions=[],
            side_effect_class="read",
            requires_approval=False,
            params={"order_id": order_id}
        )

        node2 = PlanNode(
            node_id="prepare_refund",
            role="Finance",
            instruction="Calculate and prepare the refund amount.",
            allowed_tools=["calculate_refund", "prepare_refund"],
            depends_on=("check_eligibility",),
            input_refs=["order_id", "check_eligibility"],
            output_schema={
                "type": "object",
                "properties": {
                    "refund_amount": {"type": "number"},
                    "currency": {"type": "string"}
                },
                "required": ["refund_amount", "currency"]
            },
            preconditions=["eligible == True"],
            side_effect_class="read",
            requires_approval=False,
            params={"order_id": order_id}
        )

        node3 = PlanNode(
            node_id="execute_refund",
            role="Finance",
            instruction="Execute the approved refund.",
            allowed_tools=["commit_refund"],
            depends_on=("prepare_refund",),
            input_refs=["prepare_refund"],
            output_schema={
                "type": "object",
                "properties": {
                    "refund_id": {"type": "string"},
                    "status": {"type": "string"}
                },
                "required": ["refund_id", "status"]
            },
            preconditions=["approval_received"],
            side_effect_class="write",
            requires_approval=True,
            params={"order_id": order_id}
        )

        return Plan(
            plan_id=f"refund_plan_{order_id}",
            nodes=[node1, node2, node3],
            description=f"Refund plan for order {order_id}"
        )
