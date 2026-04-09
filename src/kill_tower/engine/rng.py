from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import MutableSequence, Sequence, TypeVar

ItemT = TypeVar("ItemT")


@dataclass(slots=True)
class SeededRNG:
    seed: int
    _random: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._random = Random(self.seed)

    def randint(self, start: int, end: int) -> int:
        return self._random.randint(start, end)

    def choice(self, items: Sequence[ItemT]) -> ItemT:
        return self._random.choice(list(items))

    def shuffle(self, items: MutableSequence[ItemT]) -> None:
        self._random.shuffle(items)

    def export_state(self) -> object:
        return self._random.getstate()

    def import_state(self, state: object) -> None:
        self._random.setstate(state)