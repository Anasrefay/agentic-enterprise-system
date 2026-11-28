
from unittest.mock import patch

from routing.model_adapter import call_model


# Simulate a provider that always returns HTTP 429
rate_limit_error = Exception("Rate limit exceeded")
rate_limit_error.status_code = 429

with patch(
    "routing.model_adapter.completion",
    side_effect=rate_limit_error
) as mock_completion:

    with patch("routing.model_adapter.time.sleep") as mock_sleep:

        try:
            call_model(
                model_alias="low",
                user_prompt="Test retry exhaustion"
            )

        except RuntimeError as error:

            assert mock_completion.call_count == 3
            assert mock_sleep.call_count == 2

            print("API attempts:", mock_completion.call_count)
            print("Retry waits:", mock_sleep.call_count)
            print("Final error:", error)

            print("\nRetry exhaustion test passed!")

        else:
            raise AssertionError(
                "Expected RuntimeError after exhausting retries!"
            )
