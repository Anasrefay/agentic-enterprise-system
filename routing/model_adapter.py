
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import yaml
from dotenv import load_dotenv
from litellm import completion

MAX_RETRIES = 2
INITIAL_BACKOFF_SECONDS = 1

# Load API keys from the project's .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# Load model settings from models.yaml
CONFIG_PATH = PROJECT_ROOT / "configs" / "models.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    MODEL_CONFIG = yaml.safe_load(file)


@dataclass
class ModelResponse:
    content: str
    requested_model: str
    resolved_model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: Optional[float]


def is_retryable_error(error: Exception) -> bool:

    error_name = type(error).__name__

    retryable_errors = {
        "RateLimitError",
        "Timeout",
        "APIConnectionError",
        "ServiceUnavailableError",
        "InternalServerError",
    }

    if error_name in retryable_errors:
        return True

    status_code = getattr(error, "status_code", None)

    if status_code in [408, 409, 429, 500, 502, 503, 504]:
        return True

    return False


def call_model(
    model_alias: str,
    user_prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    temperature: Optional[float] = None,
) -> ModelResponse:

    # Check that the requested model exists
    if model_alias not in MODEL_CONFIG["models"]:
        available = list(MODEL_CONFIG["models"].keys())
        raise ValueError(
            f"Unknown model alias: {model_alias}. "
            f"Available models: {available}"
        )

    model_name = MODEL_CONFIG["models"][model_alias]["model"]

    # Prepare the conversation
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    request_options = {}

    if temperature is not None:
        request_options["temperature"] = temperature

    # Measure total response time
    start_time = time.perf_counter()

    for attempt in range(MAX_RETRIES + 1):

        try:
            response = completion(
                model=model_name,
                messages=messages,
                **request_options,
            )

            break

        except Exception as error:

            should_retry = is_retryable_error(error)
            is_last_attempt = attempt == MAX_RETRIES

            if not should_retry or is_last_attempt:
                raise RuntimeError(
                    f"Model call failed for '{model_alias}' "
                    f"({model_name}): {error}"
                ) from error

            wait_time = (
                INITIAL_BACKOFF_SECONDS * (2 ** attempt)
            )

            print(
                f"Temporary error: {type(error).__name__}. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    latency_ms = (time.perf_counter() - start_time) * 1000

    # Extract the generated answer
    content = response.choices[0].message.content or ""

    # Extract token usage
    usage = response.usage

    input_tokens = usage.prompt_tokens or 0
    output_tokens = usage.completion_tokens or 0
    total_tokens = usage.total_tokens or 0

    # Get the actual model name returned by the provider
    resolved_model = response.model or model_name

    # Get actual cost if LiteLLM provides it
    hidden_params = getattr(response, "_hidden_params", {})
    cost_usd = hidden_params.get("response_cost")

    return ModelResponse(
        content=content,
        requested_model=model_name,
        resolved_model=resolved_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=round(latency_ms, 2),
        cost_usd=cost_usd,
    )
