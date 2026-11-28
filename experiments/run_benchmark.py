
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from routing.model_adapter import call_model


TASKS_FILE = PROJECT_ROOT / "experiments" / "dev_tasks.yaml"
RESULTS_FILE = PROJECT_ROOT / "experiments" / "benchmark_results.jsonl"
CONFIG_FILE = PROJECT_ROOT / "configs" / "models.yaml"


def load_tasks():
    with open(TASKS_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)["tasks"]


def load_model_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)["models"]


def load_completed_tasks():
    completed = set()

    if not RESULTS_FILE.exists():
        return completed

    with open(RESULTS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            result = json.loads(line)

            if result.get("status") == "success":
                completed.add((
                    result["task_id"],
                    result["model_alias"],
                    result["requested_model"],
                ))

    return completed


def save_result(result):
    with open(RESULTS_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")


def run_benchmark(models, start, limit, delay):
    tasks = load_tasks()
    model_config = load_model_config()
    completed = load_completed_tasks()

    selected_tasks = tasks[start:start + limit]

    print("Tasks selected:", len(selected_tasks))
    print("Models:", ", ".join(models))
    print("-" * 50)

    for model_alias in models:
        requested_model = model_config[model_alias]["model"]

        for task in selected_tasks:

            task_key = (
                task["id"],
                model_alias,
                requested_model,
            )

            if task_key in completed:
                print(f"\nSkipping {task['id']} | {model_alias}: already successful")
                continue

            print(f"\nTask: {task['id']} | Model: {model_alias}")

            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": task["id"],
                "category": task["category"],
                "difficulty": task["difficulty"],
                "model_alias": model_alias,
                "expected_checks": task["expected_checks"],
                "evaluation": "pending",
            }

            try:
                response = call_model(
                    model_alias=model_alias,
                    user_prompt=task["prompt"],
                )

                result.update({
                    "status": "success",
                    "response": response.content,
                    "requested_model": response.requested_model,
                    "resolved_model": response.resolved_model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "latency_ms": response.latency_ms,
                    "cost_usd": response.cost_usd,
                })

                print("Status: SUCCESS")
                print("Latency:", response.latency_ms, "ms")
                print("Total tokens:", response.total_tokens)

            except Exception as error:
                result.update({
                    "status": "failed",
                    "requested_model": requested_model,
                    "error": str(error),
                })

                print("Status: FAILED")
                print(error)

            save_result(result)
            time.sleep(delay)

    print("\nBenchmark run finished.")
    print("Results saved to:", RESULTS_FILE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--models",
        default="low,medium,high",
    )

    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Starting task index (zero-based)."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of tasks to process."
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=3,
    )

    args = parser.parse_args()

    selected_models = [
        model.strip()
        for model in args.models.split(",")
        if model.strip()
    ]

    available_models = load_model_config()

    invalid_models = [
        model for model in selected_models
        if model not in available_models
    ]

    if invalid_models:
        raise ValueError(f"Unknown model aliases: {invalid_models}")

    if args.start < 0 or args.limit < 1:
        raise ValueError("Start must be >= 0 and limit must be >= 1.")

    run_benchmark(
        models=selected_models,
        start=args.start,
        limit=args.limit,
        delay=args.delay,
    )
