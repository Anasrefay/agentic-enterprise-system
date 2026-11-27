import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from orchestration.contracts.request import Request


class UnroutableRequestError(ValueError):
    """Raised when a request cannot be mapped to a supported pattern."""

@dataclass(frozen=True)
class Route:
    pattern: str
    params: dict[str, Any] = field(default_factory=dict)

_REFUND_WORDS = re.compile(r"\brefunds?\b|\brefunded\b",re.IGNORECASE,)
_ORDER_CODE = re.compile(r"\b[A-Za-z]{2,}-\d+\b")
_ORDER_NUMBER = re.compile(r"\border\s*(?:id|number|no\.?)?\s*#?\s*(\d[\w-]*)",re.IGNORECASE,)

def _refund_params(request: Request) -> dict[str, Any]:
    order_id = request.context.get("order_id")

    if order_id is None or not str(order_id).strip():
        code_match = _ORDER_CODE.search(request.goal)

        if code_match:
            order_id = code_match.group(0)
        else:
            number_match = _ORDER_NUMBER.search(request.goal)

            if number_match:
                order_id = number_match.group(1)

    if order_id is None or not str(order_id).strip():
        raise UnroutableRequestError(
            "Refund request requires an order ID."
        )

    return {"order_id": str(order_id).strip()}


_RULES: list[tuple[str, re.Pattern[str], Callable[[Request], dict[str, Any]]]] = [
    ("refund", _REFUND_WORDS, _refund_params),
]


def route(request: Request) -> Route:
    if not request.goal or not request.goal.strip():
        raise UnroutableRequestError("Request goal cannot be empty.")

    explicit_pattern = request.context.get("pattern")

    if explicit_pattern is not None:
        if not isinstance(explicit_pattern, str) or not explicit_pattern.strip():
            raise UnroutableRequestError(
                "Explicit pattern must be a non-empty string."
            )

        params = {
            key: value
            for key, value in request.context.items()
            if key != "pattern"
        }

        return Route(pattern=explicit_pattern.strip(),params=params,)

    for name, matcher, extractor in _RULES:
        if matcher.search(request.goal):
            return Route(pattern=name,params=extractor(request),)

    raise UnroutableRequestError(
        f"No pattern matches request goal: {request.goal!r}"
    )
