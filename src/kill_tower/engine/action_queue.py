from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Action:
    name: str
    source_id: str
    payload: dict[str, Any] = field(default_factory=dict)


class ActionQueue:
    def __init__(self) -> None:
        self._queue: deque[Action] = deque()

    def push(self, action: Action) -> None:
        self._queue.append(action)

    def extend(self, actions: list[Action]) -> None:
        self._queue.extend(actions)

    def pop(self) -> Action:
        return self._queue.popleft()

    def peek(self) -> Action | None:
        return self._queue[0] if self._queue else None

    def drain(self) -> list[Action]:
        items = list(self._queue)
        self._queue.clear()
        return items

    def __len__(self) -> int:
        return len(self._queue)