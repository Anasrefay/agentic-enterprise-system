"""Stub runner + stub graph so other members can integrate before model calls work."""

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.step_result import Fact, StepResult
from orchestration.contracts.task_state import TaskState


async def echo_runner(node: PlanNode, state: TaskState) -> StepResult:
    """Deterministic fake agent: succeeds and echoes the instruction."""
    return StepResult.ok(
        node.node_id,
        output={"echo": node.instruction,
                "inputs": {d: state.results[d].output for d in node.depends_on}},
        facts=(Fact(claim=f"stub result of {node.node_id}", source="stub", confidence=1.0),),
    )


def build_stub_graph() -> list[PlanNode]:
    """Diamond: research_a & research_b (parallel read) -> analyze -> write (needs approval)."""
    def n(i: str, *deps: str, approval: bool = False) -> PlanNode:
        return PlanNode(node_id=i, agent="stub", instruction=f"do {i}",
                        depends_on=deps, requires_approval=approval)
    return [
        n("research_a"),
        n("research_b"),
        n("analyze", "research_a", "research_b"),
        n("write", "analyze", approval=True),
    ]
