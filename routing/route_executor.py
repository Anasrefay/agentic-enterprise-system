
import time

from routing.model_adapter import call_model, MODEL_CONFIG
from routing.route_decision import RouteDecision
from experiments.usage_tracker import log_model_call, log_failed_call


def execute_route(
    decision: RouteDecision,
    prompt: str,
    call_role: str = "primary"
):
    
    if decision.selected_model is None:
        raise ValueError("No model was selected for this task.")

    requested_model = MODEL_CONFIG["models"][
        decision.selected_model
    ]["model"]

    start_time = time.perf_counter()

    try:
        response = call_model(
            model_alias=decision.selected_model,
            user_prompt=prompt
        )

    except Exception as error:
        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        log_failed_call(
            task_id=decision.task_id,
            call_role=call_role,
            requested_model=requested_model,
            error=error,
            latency_ms=latency_ms
        )

        raise

    log_model_call(
        task_id=decision.task_id,
        call_role=call_role,
        response=response
    )

    return response
