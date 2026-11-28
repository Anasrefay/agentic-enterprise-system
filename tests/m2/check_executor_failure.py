
from unittest.mock import patch

from routing.route_decision import RouteDecision
from routing.route_executor import execute_route


decision = RouteDecision(
    task_id="TEST_FAIL",
    task_category="business_research",
    risk_level="low",
    selected_model="low",
    requires_verification=False,
    requires_human_approval=False,
    reason="Testing failed model call"
)

fake_error = RuntimeError("Simulated provider failure")

with patch(
    "routing.route_executor.call_model",
    side_effect=fake_error
):
    with patch(
        "routing.route_executor.log_failed_call"
    ) as mock_logger:

        try:
            execute_route(
                decision,
                "Test prompt"
            )
        except RuntimeError:
            pass

        assert mock_logger.call_count == 1

        logged_call = mock_logger.call_args

        assert logged_call.kwargs["task_id"] == "TEST_FAIL"
        assert logged_call.kwargs["call_role"] == "primary"
        assert logged_call.kwargs["error"] is fake_error

print("Executor failure logging test passed!")
