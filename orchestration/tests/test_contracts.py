import pytest
from pydantic import ValidationError

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.request import SCHEMA_VERSION, Constraints, Request
from orchestration.contracts.step_result import Fact, StepResult, StepStatus
from orchestration.contracts.task_state import TaskState, TaskStatus


def node(**kw):
    base = dict(node_id="a", agent="stub", instruction="x")
    base.update(kw)
    return PlanNode(**base)


# ---- Request ----
def test_request_defaults_and_version():
    r = Request(goal="  summarize  ")
    assert r.goal == "summarize"
    assert r.schema_version == SCHEMA_VERSION
    assert r.request_id and r.constraints.max_parallel == 4


def test_request_rejects_empty_goal_and_extra_fields():
    with pytest.raises(ValidationError):
        Request(goal="   ")
    with pytest.raises(ValidationError):
        Request(goal="x", nonsense=1)


def test_constraints_bounds():
    with pytest.raises(ValidationError):
        Constraints(max_parallel=0)
    with pytest.raises(ValidationError):
        Constraints(node_timeout_s=0)


def test_request_json_roundtrip():
    r = Request(goal="x", context={"k": [1, 2]})
    assert Request.model_validate_json(r.model_dump_json()) == r


# ---- PlanNode ----
def test_plan_node_self_dependency_rejected():
    with pytest.raises(ValidationError):
        node(node_id="a", depends_on=("a",))


def test_plan_node_duplicate_dependency_rejected():
    with pytest.raises(ValidationError):
        node(node_id="c", depends_on=("a", "a"))


def test_plan_node_id_pattern():
    with pytest.raises(ValidationError):
        node(node_id="1bad id")


# ---- StepResult / Fact ----
def test_success_result_ok():
    r = StepResult.ok("a", {"x": 1})
    assert r.status is StepStatus.SUCCESS and r.reason is None


def test_failed_and_blocked_require_reason():
    with pytest.raises(ValidationError):
        StepResult(node_id="a", status=StepStatus.FAILED)
    with pytest.raises(ValidationError):
        StepResult(node_id="a", status=StepStatus.BLOCKED, reason="  ")
    assert StepResult.failed("a", "boom").reason == "boom"
    assert StepResult.blocked("a", "no input").status is StepStatus.BLOCKED


def test_success_must_not_have_reason():
    with pytest.raises(ValidationError):
        StepResult(node_id="a", status=StepStatus.SUCCESS, reason="why")


def test_fact_confidence_and_source():
    with pytest.raises(ValidationError):
        Fact(claim="c", source="s", confidence=1.5)
    with pytest.raises(ValidationError):
        Fact(claim="c", source="", confidence=0.5)
    assert Fact(claim="c", source="s", confidence=0.0).confidence == 0.0


def test_step_result_is_immutable():
    r = StepResult.ok("a")
    with pytest.raises(ValidationError):
        r.status = StepStatus.FAILED


# ---- TaskState ----
def test_task_state_new():
    s = TaskState.new(Request(goal="x"))
    assert s.status is TaskStatus.CREATED and not s.is_terminal
    assert s.nodes == {} and s.history == []


def test_task_state_json_roundtrip():
    s = TaskState.new(Request(goal="x"))
    assert TaskState.model_validate_json(s.model_dump_json()) == s
