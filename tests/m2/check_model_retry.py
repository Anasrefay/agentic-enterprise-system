
from unittest.mock import patch

from routing.model_adapter import call_model


# Test 1: Temporary error, then success
with patch(
    "routing.model_adapter.completion",
    side_effect=[
        Exception("Temporary failure"),
        "SUCCESS"
    ]
) as mock_completion:

    with patch("routing.model_adapter.time.sleep") as mock_sleep:

        # Make the first error retryable
        error = Exception("Temporary failure")
        error.status_code = 429

        mock_completion.side_effect = [
            error,
            type("FakeResponse", (), {
                "choices": [
                    type("Choice", (), {
                        "message": type("Message", (), {
                            "content": "Retry worked!"
                        })()
                    })()
                ],
                "usage": type("Usage", (), {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15
                })(),
                "model": "test-model",
                "_hidden_params": {"response_cost": 0.0}
            })()
        ]

        response = call_model(
            model_alias="low",
            user_prompt="Test retry"
        )

        assert response.content == "Retry worked!"
        assert mock_completion.call_count == 2
        assert mock_sleep.call_count == 1

        print("Temporary error retry test passed!")


# Test 2: Non-retryable error
with patch(
    "routing.model_adapter.completion",
    side_effect=ValueError("Invalid request")
) as mock_completion:

    try:
        call_model(
            model_alias="low",
            user_prompt="Test non-retryable error"
        )

    except RuntimeError:
        assert mock_completion.call_count == 1
        print("Non-retryable error test passed!")

    else:
        raise AssertionError("Expected RuntimeError was not raised!")


print("\nAll retry tests passed!")



from routing.model_adapter import is_retryable_error


# Create fake error classes
class RateLimitError(Exception):
    pass


class Timeout(Exception):
    pass


class APIConnectionError(Exception):
    pass


class ServiceUnavailableError(Exception):
    pass


class InternalServerError(Exception):
    pass


# Temporary errors should be retried
temporary_errors = [
    RateLimitError(),
    Timeout(),
    APIConnectionError(),
    ServiceUnavailableError(),
    InternalServerError(),
]

temporary_errors[0].status_code = 429
temporary_errors[3].status_code = 503
temporary_errors[4].status_code = 500

for error in temporary_errors:
    assert is_retryable_error(error) is True


# Permanent errors should not be retried
permanent_errors = [
    (400, "Bad request"),
    (401, "Authentication failed"),
    (403, "Permission denied"),
]

for status_code, message in permanent_errors:
    fake_error = Exception(message)
    fake_error.status_code = status_code

    assert is_retryable_error(fake_error) is False


print("Temporary and permanent error classification tests passed!")
