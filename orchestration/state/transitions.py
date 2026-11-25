"""Legal transition tables. Anything not listed here is illegal."""

from orchestration.contracts.task_state import NodeStatus, TaskStatus

T, N = TaskStatus, NodeStatus

TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    T.CREATED: frozenset({T.PLANNING, T.CANCELLED}),
    T.PLANNING: frozenset({T.RUNNING, T.FAILED, T.CANCELLED}),
    T.RUNNING: frozenset({T.COMPLETED, T.FAILED, T.BLOCKED, T.CANCELLED}),
    T.COMPLETED: frozenset(),
    T.BLOCKED: frozenset(),
    T.FAILED: frozenset(),
    T.CANCELLED: frozenset(),
}

NODE_TRANSITIONS: dict[NodeStatus, frozenset[NodeStatus]] = {
    N.PENDING: frozenset({N.READY, N.BLOCKED}),
    N.READY: frozenset({N.RUNNING, N.AWAITING_APPROVAL, N.BLOCKED}),
    N.AWAITING_APPROVAL: frozenset({N.READY, N.BLOCKED}),  # approved -> READY
    N.RUNNING: frozenset({N.COMPLETED, N.FAILED, N.BLOCKED}),
    N.COMPLETED: frozenset(),
    N.FAILED: frozenset(),
    N.BLOCKED: frozenset(),
}

# Targets that must come with an explicit human-readable reason.
TASK_REASON_REQUIRED = frozenset({T.FAILED, T.BLOCKED, T.CANCELLED})
NODE_REASON_REQUIRED = frozenset({N.FAILED, N.BLOCKED})


class IllegalTransition(Exception):
    """Raised when a status change is not in the transition table."""


class MissingReason(ValueError):
    """Raised when a FAILED/BLOCKED/CANCELLED transition has no reason."""


def is_legal_task(frm: TaskStatus, to: TaskStatus) -> bool:
    return to in TASK_TRANSITIONS[frm]


def is_legal_node(frm: NodeStatus, to: NodeStatus) -> bool:
    return to in NODE_TRANSITIONS[frm]
