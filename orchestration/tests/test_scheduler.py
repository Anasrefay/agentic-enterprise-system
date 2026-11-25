import asyncio

import pytest

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.request import Constraints, Request
from orchestration.contracts.step_result import StepResult
from orchestration.contracts.task_state import NodeStatus, TaskState, TaskStatus
from orchestration.scheduler.dag import DAG
from orchestration.scheduler.dependencies import (
    CycleError,
    DuplicateNodeError,
    EmptyPlanError,
    UnknownDependencyError,
    validate_dependencies,
)
from orchestration.scheduler.executor import Executor, ExecutorError
from orchestration.scheduler.stubs import build_stub_graph, echo_runner
from orchestration.state.state_machine import load_plan


def N(i, *deps, approval=False):
    return PlanNode(node_id=i, agent="stub", instruction=i, depends_on=deps,
                    requires_approval=approval)


def make_state(nodes, **constraints):
    s = TaskState.new(Request(goal="t", constraints=Constraints(**constraints)))
    load_plan(s, nodes)
    return s


def run(state, runner=echo_runner, **kw):
    return asyncio.run(Executor(runner, **kw).run(state))


DIAMOND = [N("a"), N("b", "a"), N("c", "a"), N("d", "b", "c")]


# ---------------- dependencies ----------------
def test_validate_ok_returns_map():
    assert validate_dependencies(DIAMOND)["d"] == ("b", "c")


def test_empty_plan():
    with pytest.raises(EmptyPlanError):
        validate_dependencies([])


def test_duplicate_ids():
    with pytest.raises(DuplicateNodeError):
        validate_dependencies([N("a"), N("a")])


def test_unknown_dependency():
    with pytest.raises(UnknownDependencyError):
        validate_dependencies([N("a", "ghost")])


def test_cycle_detected_with_path():
    with pytest.raises(CycleError) as e:
        validate_dependencies([N("a", "c"), N("b", "a"), N("c", "b")])
    assert "->" in str(e.value)


# ---------------- DAG ----------------
def test_topological_order_and_layers():
    dag = DAG(DIAMOND)
    assert dag.topological_order() == ["a", "b", "c", "d"]
    assert dag.layers() == [["a"], ["b", "c"], ["d"]]


def test_ready_set():
    dag = DAG(DIAMOND)
    st = {n: NodeStatus.PENDING for n in "abcd"}
    assert dag.ready(st) == ["a"]
    st["a"] = NodeStatus.COMPLETED
    assert dag.ready(st) == ["b", "c"]
    st["b"] = NodeStatus.COMPLETED
    assert dag.ready(st) == ["c"]


def test_descendants_ancestors():
    dag = DAG(DIAMOND)
    assert dag.descendants("a") == {"b", "c", "d"}
    assert dag.ancestors("d") == {"a", "b", "c"}
    assert dag.descendants("d") == set()


# ---------------- executor ----------------
def test_stub_graph_completes():
    s = make_state(build_stub_graph())
    run(s)
    assert s.status is TaskStatus.COMPLETED
    assert set(s.node_status.values()) == {NodeStatus.COMPLETED}
    assert s.approvals == {"write": True}
    assert "research_a" in s.results["analyze"].output["inputs"]


def test_dependency_order_respected():
    order = []

    async def runner(node, state):
        order.append(node.node_id)
        return StepResult.ok(node.node_id)

    run(make_state(DIAMOND), runner)
    assert order[0] == "a" and order[-1] == "d"


def test_parallel_reads_run_concurrently_and_limit_is_respected():
    async def probe(limit):
        cur = peak = 0

        async def runner(node, state):
            nonlocal cur, peak
            cur += 1
            peak = max(peak, cur)
            await asyncio.sleep(0.03)
            cur -= 1
            return StepResult.ok(node.node_id)

        nodes = [N("r1"), N("r2"), N("r3"), N("m", "r1", "r2", "r3")]
        s = make_state(nodes, max_parallel=limit)
        await Executor(runner).run(s)
        assert s.status is TaskStatus.COMPLETED
        return peak

    assert asyncio.run(probe(3)) == 3
    assert asyncio.run(probe(1)) == 1


def test_failure_blocks_descendants_and_task_fails_with_reason():
    async def runner(node, state):
        if node.node_id == "b":
            return StepResult.failed("b", "model exploded")
        return StepResult.ok(node.node_id)

    s = make_state(DIAMOND, max_retries=0)
    run(s, runner)
    assert s.status is TaskStatus.FAILED
    assert "model exploded" in s.reason
    assert s.node_status["c"] is NodeStatus.COMPLETED  # independent branch finished
    assert s.node_status["d"] is NodeStatus.BLOCKED
    assert "upstream 'b'" in s.node_reasons["d"]


def test_blocked_step_gives_blocked_task():
    async def runner(node, state):
        if node.node_id == "a":
            return StepResult.blocked("a", "missing API key")
        return StepResult.ok(node.node_id)

    s = make_state(DIAMOND)
    run(s, runner)
    assert s.status is TaskStatus.BLOCKED
    assert "missing API key" in s.reason
    assert s.attempts["a"] == 1  # BLOCKED is not retried


def test_retry_then_success():
    calls = {"n": 0}

    async def runner(node, state):
        calls["n"] += 1
        if calls["n"] == 1:
            return StepResult.failed(node.node_id, "flaky")
        return StepResult.ok(node.node_id)

    s = make_state([N("a")], max_retries=1)
    run(s, runner)
    assert s.status is TaskStatus.COMPLETED
    assert s.attempts["a"] == 2 and s.results["a"].attempt == 2


def test_retries_exhausted():
    async def runner(node, state):
        return StepResult.failed(node.node_id, "always")

    s = make_state([N("a")], max_retries=2)
    run(s, runner)
    assert s.status is TaskStatus.FAILED and s.attempts["a"] == 3


def test_runner_exception_becomes_failed_result():
    async def runner(node, state):
        raise RuntimeError("kaboom")

    s = make_state([N("a")], max_retries=0)
    run(s, runner)
    assert s.status is TaskStatus.FAILED
    assert "RuntimeError" in s.node_reasons["a"]


def test_timeout():
    async def runner(node, state):
        await asyncio.sleep(1)
        return StepResult.ok(node.node_id)

    s = make_state([N("a")], max_retries=0, node_timeout_s=0.05)
    run(s, runner)
    assert s.status is TaskStatus.FAILED and "timeout" in s.node_reasons["a"]


def test_runner_returning_wrong_node_id_is_failure():
    async def runner(node, state):
        return StepResult.ok("someone_else")

    s = make_state([N("a")], max_retries=0)
    run(s, runner)
    assert s.status is TaskStatus.FAILED


def test_approval_denied_blocks_node_and_descendants():
    async def deny(node, state):
        return False

    s = make_state([N("a"), N("b", "a", approval=True), N("c", "b")])
    run(s, echo_runner, approval_gate=deny)
    assert s.status is TaskStatus.BLOCKED
    assert s.approvals == {"b": False}
    assert s.node_status["a"] is NodeStatus.COMPLETED
    assert "approval denied" in s.node_reasons["b"]
    assert s.node_status["c"] is NodeStatus.BLOCKED
    assert "b" not in s.results  # never executed


def test_approval_gate_error_never_auto_approves():
    async def broken(node, state):
        raise ValueError("gate down")

    s = make_state([N("a", approval=True)])
    run(s, echo_runner, approval_gate=broken)
    assert s.status is TaskStatus.BLOCKED
    assert s.approvals == {"a": False}


def test_deterministic_history():
    def trace():
        s = make_state(DIAMOND)
        run(s)
        return [(h.scope, h.target_id, h.from_status, h.to_status) for h in s.history]

    assert trace() == trace()


def test_every_run_ends_terminal_with_reason_when_not_completed():
    async def runner(node, state):
        return StepResult.failed(node.node_id, "x")

    s = make_state(DIAMOND, max_retries=0)
    run(s, runner)
    assert s.is_terminal and s.reason


def test_executor_rejects_terminal_task():
    s = make_state([N("a")])
    run(s)
    with pytest.raises(ExecutorError):
        run(s)
