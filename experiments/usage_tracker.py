
import json
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parent.parent

USAGE_LOG_PATH = PROJECT_ROOT / "experiments" / "usage_log.jsonl"


def log_model_call(
    task_id: str,
    call_role: str,
    response
):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "call_role": call_role,
        "requested_model": response.requested_model,
        "resolved_model": response.resolved_model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
        "latency_ms": response.latency_ms,
        "cost_usd": response.cost_usd,
        "status": "success"
    }

    with open(USAGE_LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def get_usage_summary():
    if not USAGE_LOG_PATH.exists():
        records = []
    else:
        records = []

        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))

    successful_records = [
        record for record in records
        if record["status"] == "success"
    ]

    failed_records = [
        record for record in records
        if record["status"] == "failed"
    ]

    total_attempts = len(records)

    return {
        "total_attempts": total_attempts,
        "successful_calls": len(successful_records),
        "failed_calls": len(failed_records),

        "total_tokens": sum(
            record.get("total_tokens", 0) or 0
            for record in successful_records
        ),

        "total_cost_usd": sum(
            record.get("cost_usd") or 0.0
            for record in successful_records
        ),

        "average_latency_ms": round(
            sum(record["latency_ms"] for record in records)
            / total_attempts,
            2
        ) if total_attempts else 0.0,

        "average_success_latency_ms": round(
            sum(record["latency_ms"] for record in successful_records)
            / len(successful_records),
            2
        ) if successful_records else 0.0
    }

def log_failed_call(
    task_id: str,
    call_role: str,
    requested_model: str,
    error: Exception,
    latency_ms: float
):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "call_role": call_role,
        "requested_model": requested_model,
        "resolved_model": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "latency_ms": round(latency_ms, 2),
        "cost_usd": None,
        "status": "failed",
        "error_type": type(error).__name__,
        "error_message": str(error)
    }

    with open(USAGE_LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
