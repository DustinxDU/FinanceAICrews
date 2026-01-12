from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

from AICrews.schemas.entitlements import PolicyDecision, RuntimeLimits


@dataclass
class RunContext:
    """
    Single carrier for entitlements and execution parameters.

    Evaluated once at run entry and passed through execution layers to avoid
    split-brain policy checks.
    """

    entitlements_decision: PolicyDecision
    effective_scope: str
    byok_allowed: bool
    runtime_limits: RuntimeLimits


_current_run_context: contextvars.ContextVar[Optional[RunContext]] = contextvars.ContextVar(
    "faic_current_run_context", default=None
)


def get_current_run_context() -> Optional[RunContext]:
    return _current_run_context.get()


@contextmanager
def run_context_scope(run_context: RunContext) -> Iterator[None]:
    token = _current_run_context.set(run_context)
    try:
        yield
    finally:
        _current_run_context.reset(token)
