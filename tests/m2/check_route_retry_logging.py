
from unittest.mock import patch

from routing.route_decision import RouteDecision
from routing.route_executor import execute_route


decision = RouteDecision(
    task_id="RETRY_TEST",
    task_category="business_research",
    risk_level="low",
    selected_model="low",
    requires_verification=False,
    requires_human_approval=False,
    reason="Testing retry failure logging"
)

rate_limit_error = RuntimeError("Simulated final 429 failure")

with patch(
    "routing.route_executor.call_model",
    side_effect=rate_limit_error
):

    with patch(
        "routing.route_executor.log_failed_call"
    ) as mock_log:

        try:
            execute_route(
                decision=decision,
                prompt="Test final failure logging"
            )

        except RuntimeError:
            assert mock_log.call_count == 1

            logged_call = mock_log.call_args.kwargs

            assert logged_call["task_id"] == "RETRY_TEST"
            assert logged_call["call_role"] == "primary"
            assert logged_call["error"] is rate_limit_error

            print("Failed call logged:", mock_log.call_count)
            print("Task ID:", logged_call["task_id"])
            print("Call role:", logged_call["call_role"])

            print("\nRoute retry logging test passed!")

        else:
            raise AssertionError("Expected RuntimeError!")
