"""Async executor: runs ready nodes in waves, merges results deterministically.

Contract with Person 2:
  * `NodeRunner`: async callable (node, state) -> StepResult. Runners must treat
    `state` as READ-ONLY; only the executor mutates it.
  * `ApprovalGate`: async callable (node, state) -> bool, used for nodes with
    requires_approval=True (M5's review area).
"""

import asyncio
from typing import Protocol

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.step_result import StepResult, StepStatus
from orchestration.contracts.task_state import NodeStatus, TaskState, TaskStatus
from orchestration.scheduler.dag import DAG
from orchestration.state.state_machine import start, transition_node, transition_task


class NodeRunner(Protocol):
    async def __call__(self, node: PlanNode, state: TaskState) -> StepResult: ...


class ApprovalGate(Protocol):
    async def __call__(self, node: PlanNode, state: TaskState) -> bool: ...


async def auto_approve(node: PlanNode, state: TaskState) -> bool:
    return True


class ExecutorError(RuntimeError):
    pass


_STATUS_MAP = {
    StepStatus.SUCCESS: NodeStatus.COMPLETED,
    StepStatus.FAILED: NodeStatus.FAILED,
    StepStatus.BLOCKED: NodeStatus.BLOCKED,
}


class Executor:
    def __init__(self, runner: NodeRunner, approval_gate: ApprovalGate = auto_approve,
                 max_parallel: int | None = None):
        self._runner = runner
        self._gate = approval_gate
        self._max_parallel = max_parallel

    async def run(self, state: TaskState) -> TaskState:
        """Drive the task to a terminal state: COMPLETED, BLOCKED or FAILED."""
        if state.status is TaskStatus.PLANNING:
            start(state)
        if state.status is not TaskStatus.RUNNING:
            raise ExecutorError(f"cannot run a task in state '{state.status.value}'")

        dag = DAG(state.nodes.values())
        limit = self._max_parallel or state.request.constraints.max_parallel
        sem = asyncio.Semaphore(limit)

        while True:
            ready = dag.ready(state.node_status)
            if not ready:
                break
            runnable = [nid for nid in ready if await self._admit(state, dag, nid)]
            for nid in runnable:
                transition_node(state, nid, NodeStatus.RUNNING)
            results = await asyncio.gather(
                *(self._execute(state, state.nodes[nid], sem) for nid in runnable))
            # Merge in sorted node order (runnable is sorted) -> deterministic.
            for nid, result in zip(runnable, results):
                self._apply(state, dag, nid, result)

        self._finalize(state)
        return state

    # ---- steps -------------------------------------------------------
    async def _admit(self, state: TaskState, dag: DAG, nid: str) -> bool:
        """PENDING -> READY (and the approval round-trip). False = not runnable."""
        node = state.nodes[nid]
        transition_node(state, nid, NodeStatus.READY)
        if not node.requires_approval:
            return True
        transition_node(state, nid, NodeStatus.AWAITING_APPROVAL)
        try:
            approved = await self._gate(node, state)
            denial = f"approval denied for '{nid}'"
        except Exception as exc:  # a broken gate must never auto-approve
            approved = False
            denial = f"approval gate error for '{nid}': {type(exc).__name__}: {exc}"
        state.approvals[nid] = approved
        if approved:
            transition_node(state, nid, NodeStatus.READY)
            return True
        transition_node(state, nid, NodeStatus.BLOCKED, denial)
        self._block_descendants(state, dag, nid, "blocked")
        return False

    async def _execute(self, state: TaskState, node: PlanNode,
                       sem: asyncio.Semaphore) -> StepResult:
        c = state.request.constraints
        result: StepResult | None = None
        for attempt in range(1, c.max_retries + 2):
            async with sem:
                try:
                    result = await asyncio.wait_for(
                        self._runner(node, state), timeout=c.node_timeout_s)
                    if result.node_id != node.node_id:
                        result = StepResult.failed(
                            node.node_id,
                            f"runner returned result for '{result.node_id}'")
                except asyncio.TimeoutError:
                    result = StepResult.failed(
                        node.node_id, f"timeout after {c.node_timeout_s}s")
                except Exception as exc:
                    result = StepResult.failed(
                        node.node_id, f"{type(exc).__name__}: {exc}")
            if result.status is not StepStatus.FAILED:
                break  # SUCCESS or BLOCKED: no retry
        assert result is not None
        return result.model_copy(update={"attempt": attempt})

    def _apply(self, state: TaskState, dag: DAG, nid: str, result: StepResult) -> None:
        state.results[nid] = result
        state.attempts[nid] = result.attempt
        new = _STATUS_MAP[result.status]
        transition_node(state, nid, new, result.reason)
        if new is not NodeStatus.COMPLETED:
            self._block_descendants(state, dag, nid, new.value)

    @staticmethod
    def _block_descendants(state: TaskState, dag: DAG, nid: str, why: str) -> None:
        for d in sorted(dag.descendants(nid)):
            if state.node_status[d] is NodeStatus.PENDING:
                transition_node(state, d, NodeStatus.BLOCKED, f"upstream '{nid}' {why}")

    @staticmethod
    def _finalize(state: TaskState) -> None:
        for nid in sorted(state.node_status):  # safety net, should not trigger
            if state.node_status[nid] is NodeStatus.PENDING:
                transition_node(state, nid, NodeStatus.BLOCKED, "never became ready")
        by = {s: sorted(n for n, v in state.node_status.items() if v is s)
              for s in (NodeStatus.FAILED, NodeStatus.BLOCKED)}
        if not by[NodeStatus.FAILED] and not by[NodeStatus.BLOCKED]:
            transition_task(state, TaskStatus.COMPLETED)
        elif by[NodeStatus.FAILED]:
            msg = "; ".join(f"{n}: {state.node_reasons[n]}" for n in by[NodeStatus.FAILED])
            transition_task(state, TaskStatus.FAILED, f"failed nodes -> {msg}")
        else:
            msg = "; ".join(f"{n}: {state.node_reasons[n]}" for n in by[NodeStatus.BLOCKED])
            transition_task(state, TaskStatus.BLOCKED, f"blocked nodes -> {msg}")
