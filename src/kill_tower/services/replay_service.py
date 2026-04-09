from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ReplayEvent:
    turn: int
    action: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReplayLog:
    seed: int
    events: list[ReplayEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReplayService:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.events: list[ReplayEvent] = []

    def record(self, turn: int, action: str, payload: dict[str, Any] | None = None) -> None:
        self.events.append(ReplayEvent(turn=turn, action=action, payload=payload or {}))

    def build(self) -> ReplayLog:
        return ReplayLog(seed=self.seed, events=list(self.events))