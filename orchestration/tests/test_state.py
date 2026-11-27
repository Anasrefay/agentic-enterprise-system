import pytest

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.request import Request
from orchestration.contracts.task_state import (
    TERMINAL_NODE,
    TERMINAL_TASK,
    NodeStatus,
    TaskState,
    TaskStatus,
)
from orchestration.scheduler.dependencies import CycleError
from orchestration.state.state_machine import (
    load_plan,
    start,
    transition_node,
    transition_task,
)
from orchestration.state.transitions import (
    NODE_TRANSITIONS,
    TASK_TRANSITIONS,
    IllegalTransition,
    MissingReason,
)


def N(i, *deps):
    return PlanNode(
        node_id=i,
        role="stub",
        instruction=i,
        depends_on=deps,
        output_schema={"type": "object"},
        side_effect_class="read",
    )

def fresh():
    return TaskState.new(Request(goal="x"))


def test_tables_cover_every_status():
    assert set(TASK_TRANSITIONS) == set(TaskStatus)
    assert set(NODE_TRANSITIONS) == set(NodeStatus)


def test_terminal_states_have_no_outgoing_transitions():
    for s in TERMINAL_TASK:
        assert TASK_TRANSITIONS[s] == frozenset()
    for s in TERMINAL_NODE:
        assert NODE_TRANSITIONS[s] == frozenset()


def test_task_happy_path_and_history():
    s = fresh()
    load_plan(s, [N("a")])
    assert s.status is TaskStatus.PLANNING
    start(s)
    transition_task(s, TaskStatus.COMPLETED)
    assert s.is_terminal
    assert [(h.from_status, h.to_status) for h in s.history if h.scope == "task"] == [
        ("created", "planning"), ("planning", "running"), ("running", "completed")]


@pytest.mark.parametrize("frm,to", [
    (TaskStatus.CREATED, TaskStatus.RUNNING),
    (TaskStatus.CREATED, TaskStatus.COMPLETED),
    (TaskStatus.PLANNING, TaskStatus.COMPLETED),
])
def test_illegal_task_transitions(frm, to):
    s = fresh()
    s.status = frm
    with pytest.raises(IllegalTransition):
        transition_task(s, to, "r")


def test_cannot_leave_terminal_task_state():
    s = fresh()
    s.status = TaskStatus.COMPLETED
    with pytest.raises(IllegalTransition):
        transition_task(s, TaskStatus.RUNNING)


def test_failed_and_blocked_task_need_reason():
    for target in (TaskStatus.FAILED, TaskStatus.BLOCKED):
        s = fresh()
        s.status = TaskStatus.RUNNING
        with pytest.raises(MissingReason):
            transition_task(s, target)
        transition_task(s, target, "because")
        assert s.reason == "because"


def test_node_happy_path_with_approval():
    s = fresh()
    load_plan(s, [N("a")])
    for to in (NodeStatus.READY, NodeStatus.AWAITING_APPROVAL, NodeStatus.READY,
               NodeStatus.RUNNING, NodeStatus.COMPLETED):
        transition_node(s, "a", to)
    assert s.node_status["a"] is NodeStatus.COMPLETED


def test_illegal_node_transitions():
    s = fresh()
    load_plan(s, [N("a")])
    with pytest.raises(IllegalTransition):
        transition_node(s, "a", NodeStatus.RUNNING)  # PENDING -> RUNNING
    with pytest.raises(IllegalTransition):
        transition_node(s, "a", NodeStatus.COMPLETED)
    transition_node(s, "a", NodeStatus.BLOCKED, "why")
    with pytest.raises(IllegalTransition):
        transition_node(s, "a", NodeStatus.READY)  # terminal


def test_node_failed_blocked_need_reason_and_it_is_stored():
    s = fresh()
    load_plan(s, [N("a"), N("b")])
    transition_node(s, "a", NodeStatus.BLOCKED, "no input")
    assert s.node_reasons["a"] == "no input"
    transition_node(s, "b", NodeStatus.READY)
    transition_node(s, "b", NodeStatus.RUNNING)
    with pytest.raises(MissingReason):
        transition_node(s, "b", NodeStatus.FAILED)
    # a failed attempt must not have changed anything
    assert s.node_status["b"] is NodeStatus.RUNNING


def test_unknown_node():
    s = fresh()
    load_plan(s, [N("a")])
    with pytest.raises(KeyError):
        transition_node(s, "zzz", NodeStatus.READY)


def test_load_plan_invalid_fails_task_with_reason():
    s = fresh()
    with pytest.raises(CycleError):
        load_plan(s, [N("a", "b"), N("b", "a")])
    assert s.status is TaskStatus.FAILED
    assert "cycle" in s.reason


def test_load_plan_sets_all_pending():
    s = fresh()
    load_plan(s, [N("a"), N("b", "a")])
    assert set(s.node_status.values()) == {NodeStatus.PENDING}


def test_load_plan_rejected_when_running():
    s = fresh()
    load_plan(s, [N("a")])
    start(s)
    with pytest.raises(IllegalTransition):
        load_plan(s, [N("a")])
