
import asyncio

from orchestration.contracts.request import Request, Constraints
from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.task_state import TaskState, TaskStatus, NodeStatus

from orchestration.state.state_machine import load_plan
from orchestration.scheduler.executor import Executor

from routing.node_runner import model_node_runner


async def main():

    # 1. Create a real request
    request = Request(
        goal="Test M2 integration with a real language model.",
        constraints=Constraints(
            max_parallel=1,
            max_retries=0,
            node_timeout_s=90
        )
    )

    state = TaskState.new(request)

    # 2. Create one simple read-only node
    node = PlanNode(
        node_id="model_test",
        role="Support",
        instruction=(
            "Reply with a short sentence confirming "
            "that the model integration works."
        ),
        allowed_tools=[],
        depends_on=(),
        input_refs=[],
        output_schema={"type": "object"},
        preconditions=[],
        side_effect_class="read",
        requires_approval=False,
        params={
            "task_category": "business_research",
            "risk_level": "low"
        }
    )

    # 3. Install the plan
    load_plan(state, [node])

    # 4. Run the real Member 1 Executor + Member 2 Runner
    executor = Executor(runner=model_node_runner)

    final_state = await executor.run(state)

    # 5. Check and display the result
    print("\nTASK STATUS:", final_state.status.value)
    print("NODE STATUS:", final_state.node_status["model_test"].value)

    if final_state.status == TaskStatus.COMPLETED:
        result = final_state.results["model_test"]

        print("\nMODEL RESPONSE:")
        print(result.output["content"])

        print("\nMODEL:", result.output["model"])
        print("TOKENS:", result.output["total_tokens"])
        print("LATENCY:", result.output["latency_ms"], "ms")
        print("COST:", result.output["cost_usd"])

        print("\nREAL INTEGRATION TEST PASSED!")

    else:
        print("\nINTEGRATION TEST FAILED")
        print("Reason:", final_state.reason)
        print("Node reason:", final_state.node_reasons.get("model_test"))


if __name__ == "__main__":
    asyncio.run(main())
