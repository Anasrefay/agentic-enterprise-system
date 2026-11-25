"""Request contract: what enters the system.

Schema is versioned via SCHEMA_VERSION. Bump the MINOR on additive changes and
the MAJOR on breaking ones; every contract model carries `schema_version`.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Constraints(BaseModel):
    """Execution limits attached to a request (read by the scheduler)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_parallel: int = Field(default=4, ge=1, le=32)
    max_retries: int = Field(default=1, ge=0, le=5)  # retries after the 1st attempt
    node_timeout_s: float = Field(default=60.0, gt=0)


class Request(BaseModel):
    """A user goal plus context and limits."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    schema_version: str = SCHEMA_VERSION
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    goal: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: Constraints = Field(default_factory=Constraints)
    created_at: datetime = Field(default_factory=utcnow)
