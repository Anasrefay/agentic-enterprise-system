import inspect
from collections.abc import Callable
from typing import Any

from orchestration.contracts.plan import Plan
from orchestration.supervisor.planner import Planner


PatternFn = Callable[..., Plan]
_REGISTRY: dict[str, PatternFn] = {}

class UnknownPatternError(ValueError):
    pass

class InvalidPatternParamsError(ValueError):
    pass

def register_pattern(name: str) -> Callable[[PatternFn], PatternFn]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Pattern name cannot be empty.")

    name = name.strip()

    def decorator(fn: PatternFn) -> PatternFn:
        if not callable(fn):
            raise TypeError("Pattern must be callable.")

        if name in _REGISTRY:
            raise ValueError(f"Pattern '{name}' is already registered.")

        _REGISTRY[name] = fn
        return fn

    return decorator


def get_pattern(name: str) -> PatternFn:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownPatternError(f"Unknown pattern '{name}'. "f"Available patterns: {', '.join(available_patterns())}") from None


def available_patterns() -> list[str]:
    return sorted(_REGISTRY)


def make_plan(name: str,params: dict[str, Any] | None = None,) -> Plan:
    if not isinstance(name, str) or not name.strip():
        raise UnknownPatternError("Pattern name cannot be empty.")

    name = name.strip()
    fn = get_pattern(name)
    params = {} if params is None else params

    if not isinstance(params, dict):
        raise InvalidPatternParamsError(f"Parameters for pattern '{name}' must be a dictionary.")

    try:
        inspect.signature(fn).bind(**params)
    except TypeError as exc:
        raise InvalidPatternParamsError(f"Invalid parameters for pattern '{name}': {exc}") from None

    try:
        plan = fn(**params)
    except (TypeError, ValueError) as exc:
        raise InvalidPatternParamsError(f"Could not create pattern '{name}': {exc}") from exc

    if not isinstance(plan, Plan):
        raise TypeError(f"Pattern '{name}' must return a Plan instance.")

    return plan


@register_pattern("refund")
def refund_pattern(order_id: str) -> Plan:
    return Planner().create_refund_plan(order_id)
