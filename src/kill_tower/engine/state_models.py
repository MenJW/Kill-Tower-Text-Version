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
    name: str | None = None
    card_type: str | None = None
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

    def get_power(self, power_id: str) -> int:
        return self.powers.get(power_id, 0)

    def add_power(self, power_id: str, amount: int) -> None:
        if amount == 0:
            return
        new_value = self.powers.get(power_id, 0) + amount
        if new_value <= 0:
            self.powers.pop(power_id, None)
            return
        self.powers[power_id] = new_value

    def reduce_power(self, power_id: str, amount: int) -> None:
        self.add_power(power_id, -amount)


@dataclass(slots=True)
class PlayerState(CombatantState):
    character_id: str | None = None
    energy: int = 3
    max_energy: int = 3
    gold: int = 0
    draw_pile: list[CardInstance] = field(default_factory=list)
    hand: list[CardInstance] = field(default_factory=list)
    discard_pile: list[CardInstance] = field(default_factory=list)
    exhaust_pile: list[CardInstance] = field(default_factory=list)
    relic_ids: list[str] = field(default_factory=list)
    potion_ids: list[str] = field(default_factory=list)
    resources: dict[str, int] = field(default_factory=dict)
    orbs: list[str] = field(default_factory=list)
    orb_slots: int = 3

    def get_resource(self, resource_id: str) -> int:
        return self.resources.get(resource_id, 0)

    def add_resource(self, resource_id: str, amount: int) -> None:
        if amount == 0:
            return
        new_value = self.resources.get(resource_id, 0) + amount
        if new_value <= 0:
            self.resources.pop(resource_id, None)
            return
        self.resources[resource_id] = new_value


@dataclass(slots=True)
class MonsterState(CombatantState):
    definition_id: str | None = None
    intent: str | None = None
    current_move_id: str | None = None
    move_cursor: int = 0
    move_history: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CombatState:
    seed: int
    player: PlayerState
    enemies: list[MonsterState] = field(default_factory=list)
    snapshot_tag: str | None = None
    encounter_id: str | None = None
    turn: int = 1
    phase: CombatPhase = CombatPhase.PLAYER
    victory: bool | None = None
    transcript: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RunState:
    snapshot_tag: str | None = None
    current_act: int = 1
    current_floor: int = 0
    combat: CombatState | None = None