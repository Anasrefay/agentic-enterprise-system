
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from experiments.usage_tracker import log_failed_call


with tempfile.TemporaryDirectory() as temp_dir:

    test_log = Path(temp_dir) / "test_usage.jsonl"

    fake_error = RuntimeError("Simulated provider failure")

    with patch(
        "experiments.usage_tracker.USAGE_LOG_PATH",
        test_log
    ):
        log_failed_call(
            task_id="TEST_FAIL",
            call_role="primary",
            requested_model="openrouter/test-model",
            error=fake_error,
            latency_ms=1500
        )

    with open(test_log, "r", encoding="utf-8") as file:
        record = json.loads(file.readline())

    assert record["status"] == "failed"
    assert record["task_id"] == "TEST_FAIL"
    assert record["error_type"] == "RuntimeError"
    assert record["latency_ms"] == 1500

    print("FAILED CALL RECORD:")
    print(json.dumps(record, indent=4))

    print("\nFailed call logging test passed!")
