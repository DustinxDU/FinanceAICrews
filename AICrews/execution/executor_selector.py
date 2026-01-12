from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ExecutorMode = Literal["kickoff", "agent_executor"]


@dataclass(frozen=True)
class ExecutorSelector:
    mode: ExecutorMode = "kickoff"

