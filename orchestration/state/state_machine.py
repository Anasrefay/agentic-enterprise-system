"""Functions that mutate TaskState safely (validate -> apply -> record)."""

from collections.abc import Sequence

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.task_state import (
    NodeStatus,
    TaskState,
    TaskStatus,
    TransitionRecord,
)
from orchestration.scheduler.dependencies import DependencyError, validate_dependencies
from orchestration.state.transitions import (
    NODE_REASON_REQUIRED,
    TASK_REASON_REQUIRED,
    IllegalTransition,
    MissingReason,
    is_legal_node,
    is_legal_task,
)


def transition_task(state: TaskState, to: TaskStatus, reason: str | None = None) -> None:
    frm = state.status
    if not is_legal_task(frm, to):
        raise IllegalTransition(f"task: {frm.value} -> {to.value} is not allowed")
    if to in TASK_REASON_REQUIRED and not (reason and reason.strip()):
        raise MissingReason(f"task -> {to.value} requires a reason")
    state.status = to
    if to in TASK_REASON_REQUIRED:
        state.reason = reason
    state.history.append(TransitionRecord(
        scope="task", target_id=None, from_status=frm.value,
        to_status=to.value, reason=reason))


def transition_node(state: TaskState, node_id: str, to: NodeStatus,
                    reason: str | None = None) -> None:
    if node_id not in state.node_status:
        raise KeyError(f"unknown node '{node_id}'")
    frm = state.node_status[node_id]
    if not is_legal_node(frm, to):
        raise IllegalTransition(f"node '{node_id}': {frm.value} -> {to.value} is not allowed")
    if to in NODE_REASON_REQUIRED and not (reason and reason.strip()):
        raise MissingReason(f"node '{node_id}' -> {to.value} requires a reason")
    state.node_status[node_id] = to
    if to in NODE_REASON_REQUIRED:
        state.node_reasons[node_id] = reason  # type: ignore[assignment]
    state.history.append(TransitionRecord(
        scope="node", target_id=node_id, from_status=frm.value,
        to_status=to.value, reason=reason))


def load_plan(state: TaskState, nodes: Sequence[PlanNode]) -> None:
    """Install a plan: CREATED -> PLANNING, validate deps, set all nodes PENDING.

    On an invalid plan the task goes to FAILED with the explicit reason and the
    DependencyError is re-raised.
    """
    if state.status is TaskStatus.CREATED:
        transition_task(state, TaskStatus.PLANNING)
    if state.status is not TaskStatus.PLANNING:
        raise IllegalTransition(f"cannot load a plan while task is {state.status.value}")
    try:
        validate_dependencies(nodes)
    except DependencyError as exc:
        transition_task(state, TaskStatus.FAILED, f"invalid plan: {exc}")
        raise
    state.nodes = {n.node_id: n for n in nodes}
    state.node_status = {n.node_id: NodeStatus.PENDING for n in nodes}


def start(state: TaskState) -> None:
    """PLANNING -> RUNNING."""
    transition_task(state, TaskStatus.RUNNING)
