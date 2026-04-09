from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CombatPhase(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    RESOLUTION = "resolution"


@dataclass(slots=True)
class CardInstance:
    definition_id: str
    instance_id: str
    cost: int
    upgraded: bool = False
    temporary: bool = False


@dataclass(slots=True)
class CombatantState:
    combatant_id: str
    name: str
    max_hp: int
    hp: int
    block: int = 0
    powers: dict[str, int] = field(default_factory=dict)

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass(slots=True)
class PlayerState(CombatantState):
    energy: int = 3
    max_energy: int = 3
    gold: int = 0
    draw_pile: list[CardInstance] = field(default_factory=list)
    hand: list[CardInstance] = field(default_factory=list)
    discard_pile: list[CardInstance] = field(default_factory=list)
    exhaust_pile: list[CardInstance] = field(default_factory=list)
    relic_ids: list[str] = field(default_factory=list)
    potion_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MonsterState(CombatantState):
    intent: str | None = None
    move_history: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CombatState:
    seed: int
    player: PlayerState
    enemies: list[MonsterState] = field(default_factory=list)
    turn: int = 1
    phase: CombatPhase = CombatPhase.PLAYER
    transcript: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RunState:
    snapshot_tag: str | None = None
    current_act: int = 1
    current_floor: int = 0
    combat: CombatState | None = None