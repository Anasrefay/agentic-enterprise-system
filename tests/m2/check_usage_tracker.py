
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from experiments.usage_tracker import (
    log_model_call,
    log_failed_call,
    get_usage_summary
)


class FakeResponse:
    requested_model = "test-model"
    resolved_model = "test-model"
    input_tokens = 100
    output_tokens = 50
    total_tokens = 150
    latency_ms = 2000
    cost_usd = 0.01


with tempfile.TemporaryDirectory() as temp_dir:

    test_log = Path(temp_dir) / "test_usage.jsonl"

    with patch(
        "experiments.usage_tracker.USAGE_LOG_PATH",
        test_log
    ):

        # Record one successful call
        log_model_call(
            task_id="TEST01",
            call_role="primary",
            response=FakeResponse()
        )

        # Record one failed call
        log_failed_call(
            task_id="TEST02",
            call_role="fallback",
            requested_model="test-model",
            error=RuntimeError("Simulated failure"),
            latency_ms=1500
        )

        summary = get_usage_summary()

        print("USAGE SUMMARY")
        print("==============================")

        for key, value in summary.items():
            print(f"{key}: {value}")

        # Verify accounting
        assert summary["total_attempts"] == 2
        assert summary["successful_calls"] == 1
        assert summary["failed_calls"] == 1
        assert summary["total_tokens"] == 150
        assert summary["total_cost_usd"] == 0.01
        assert summary["average_latency_ms"] == 1750
        assert summary["average_success_latency_ms"] == 2000

        print("\nUsage accounting test passed!")
