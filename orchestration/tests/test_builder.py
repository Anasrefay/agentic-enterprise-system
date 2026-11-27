
import pytest

from orchestration.contracts.plan import Plan
from orchestration.contracts.request import Request
from orchestration.contracts.task_state import TaskState
from orchestration.supervisor import builder
from orchestration.supervisor.builder import (
    PlanPolicyError,
    build_refund_task,
    build_task_state,
    check_policy,
)
from orchestration.supervisor.planner import Planner


def create_plan():
    return Planner().create_refund_plan("ORD-101")


def test_check_policy_accepts_valid_plan():
    plan = create_plan()

    check_policy(plan)


def test_check_policy_rejects_write_without_approval():
    plan = create_plan()

    unsafe_nodes = [
        node.model_copy(update={"requires_approval": False})
        if node.side_effect_class == "write"
        else node
        for node in plan.nodes
    ]

    unsafe_plan = plan.model_copy(update={"nodes": unsafe_nodes})

    with pytest.raises(PlanPolicyError):
        check_policy(unsafe_plan)


def test_build_task_state_returns_task_state(monkeypatch):
    request = Request(goal="Process refund for order ORD-101")
    plan = create_plan()
    loaded = {}

    def fake_load_plan(state, nodes):
        loaded["state"] = state
        loaded["nodes"] = nodes

    monkeypatch.setattr(builder, "load_plan", fake_load_plan)

    state = build_task_state(request, plan)

    assert isinstance(state, TaskState)
    assert loaded["state"] is state
    assert loaded["nodes"] == plan.nodes


def test_build_task_state_checks_policy(monkeypatch):
    request = Request(goal="Process refund for order ORD-101")
    plan = create_plan()

    unsafe_nodes = [
        node.model_copy(update={"requires_approval": False})
        if node.side_effect_class == "write"
        else node
        for node in plan.nodes
    ]

    unsafe_plan = plan.model_copy(update={"nodes": unsafe_nodes})

    def fake_load_plan(state, nodes):
        pytest.fail("load_plan should not be called for an unsafe plan")

    monkeypatch.setattr(builder, "load_plan", fake_load_plan)

    with pytest.raises(PlanPolicyError):
        build_task_state(request, unsafe_plan)


def test_build_refund_task_rejects_empty_order_id():
    with pytest.raises(ValueError, match="order_id cannot be empty"):
        build_refund_task("")


def test_build_refund_task_rejects_whitespace_order_id():
    with pytest.raises(ValueError, match="order_id cannot be empty"):
        build_refund_task("   ")


def test_build_refund_task_rejects_invalid_order_id_type():
    with pytest.raises(ValueError, match="order_id cannot be empty"):
        build_refund_task(None)


def test_build_refund_task_uses_planner(monkeypatch):
    plan = create_plan()
    captured = {}

    class FakePlanner:
        def create_refund_plan(self, order_id):
            captured["order_id"] = order_id
            return plan

    expected_state = object()

    def fake_build_task_state(request, received_plan):
        captured["request"] = request
        captured["plan"] = received_plan
        return expected_state

    monkeypatch.setattr(
        builder,
        "build_task_state",
        fake_build_task_state,
    )

    result = build_refund_task(
        " ORD-101 ",
        planner=FakePlanner(),
    )

    assert result is expected_state
    assert captured["order_id"] == "ORD-101"
    assert captured["plan"] is plan
    assert isinstance(captured["request"], Request)
    assert "ORD-101" in captured["request"].goal


def test_build_refund_task_uses_provided_request(monkeypatch):
    plan = create_plan()
    request = Request(goal="My refund request")
    captured = {}

    class FakePlanner:
        def create_refund_plan(self, order_id):
            return plan

    def fake_build_task_state(received_request, received_plan):
        captured["request"] = received_request
        captured["plan"] = received_plan
        return "built"

    monkeypatch.setattr(
        builder,
        "build_task_state",
        fake_build_task_state,
    )

    result = build_refund_task(
        "ORD-101",
        request=request,
        planner=FakePlanner(),
    )

    assert result == "built"
    assert captured["request"] is request
    assert captured["plan"] is plan
