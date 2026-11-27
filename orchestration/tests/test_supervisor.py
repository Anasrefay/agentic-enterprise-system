
import pytest
from pydantic import ValidationError

from orchestration.contracts.request import Request
from orchestration.supervisor.routing import (
    Route,
    UnroutableRequestError,
    route,
)
from orchestration.supervisor.patterns import (
    InvalidPatternParamsError,
    UnknownPatternError,
    available_patterns,
    make_plan,
)


def create_request(goal, context=None):
    return Request(
        goal=goal,
        context=context or {},
    )


def test_route_refund_with_order_code():
    request = create_request("I want a refund for order ORD-101")

    result = route(request)

    assert isinstance(result, Route)
    assert result.pattern == "refund"
    assert result.params == {"order_id": "ORD-101"}


def test_route_refund_with_order_number():
    request = create_request("I want a refund for order number 101")

    result = route(request)

    assert result.pattern == "refund"
    assert result.params == {"order_id": "101"}


def test_route_refund_using_context():
    request = create_request(
        "I want a refund",
        {"order_id": "ORD-205"},
    )

    result = route(request)

    assert result.pattern == "refund"
    assert result.params == {"order_id": "ORD-205"}


def test_route_with_explicit_pattern():
    request = create_request(
        "Process this request",
        {
            "pattern": "refund",
            "order_id": "ORD-300",
        },
    )

    result = route(request)

    assert result.pattern == "refund"
    assert result.params == {"order_id": "ORD-300"}


def test_route_refund_without_order_id():
    request = create_request("I want a refund")

    with pytest.raises(UnroutableRequestError):
        route(request)


def test_route_unsupported_request():
    request = create_request("I want to update my profile")

    with pytest.raises(UnroutableRequestError):
        route(request)


def test_request_rejects_empty_goal():
    with pytest.raises(ValidationError):
        create_request("   ")


def test_available_patterns():
    assert "refund" in available_patterns()


def test_make_refund_plan():
    plan = make_plan("refund", {"order_id": "ORD-101"})

    assert len(plan.nodes) == 3
    assert [node.node_id for node in plan.nodes] == [
        "check_eligibility",
        "prepare_refund",
        "execute_refund",
    ]


def test_refund_plan_dependencies():
    plan = make_plan("refund", {"order_id": "ORD-101"})

    assert plan.nodes[0].depends_on == ()
    assert plan.nodes[1].depends_on == ("check_eligibility",)
    assert plan.nodes[2].depends_on == ("prepare_refund",)


def test_refund_execution_requires_approval():
    plan = make_plan("refund", {"order_id": "ORD-101"})

    execute_node = plan.nodes[2]

    assert execute_node.side_effect_class == "write"
    assert execute_node.requires_approval is True


def test_refund_plan_order_id():
    plan = make_plan("refund", {"order_id": "ORD-101"})

    for node in plan.nodes:
        assert node.params["order_id"] == "ORD-101"


def test_make_plan_unknown_pattern():
    with pytest.raises(UnknownPatternError):
        make_plan("unknown_pattern", {})


def test_make_plan_missing_required_parameter():
    with pytest.raises(InvalidPatternParamsError):
        make_plan("refund", {})


def test_make_plan_rejects_extra_parameter():
    with pytest.raises(InvalidPatternParamsError):
        make_plan(
            "refund",
            {
                "order_id": "ORD-101",
                "extra": "value",
            },
        )
