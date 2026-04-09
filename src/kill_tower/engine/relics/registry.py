from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from kill_tower.engine.turn_system import draw_cards

if TYPE_CHECKING:
    from kill_tower.engine.combat.runtime import CombatRuntime

RelicHook = Callable[["CombatRuntime"], None]


@dataclass(frozen=True, slots=True)
class RelicHooks:
    on_combat_start: RelicHook | None = None
    on_player_turn_start: RelicHook | None = None
    on_combat_end: RelicHook | None = None


def ring_of_the_snake_on_combat_start(runtime: "CombatRuntime") -> None:
    draw_cards(runtime.player, 2, runtime.rng)
    runtime.log(f"Ring of the Snake draws 2 additional cards for {runtime.player.name}.")


def cracked_core_on_combat_start(runtime: "CombatRuntime") -> None:
    runtime.channel_orb("lightning-orb", "Cracked Core")


def divine_right_on_combat_start(runtime: "CombatRuntime") -> None:
    runtime.gain_resource("star", 3, "Divine Right")


def bound_phylactery_on_player_turn_start(runtime: "CombatRuntime") -> None:
    runtime.gain_resource("osty_hp", 1, "Bound Phylactery")


def burning_blood_on_combat_end(runtime: "CombatRuntime") -> None:
    player = runtime.state.player
    previous_hp = player.hp
    player.hp = min(player.max_hp, player.hp + 6)
    healed = player.hp - previous_hp
    if healed > 0:
        runtime.log(f"Burning Blood heals {player.name} for {healed} HP.")


RELIC_HOOKS: dict[str, RelicHooks] = {
    "ring-of-the-snake": RelicHooks(on_combat_start=ring_of_the_snake_on_combat_start),
    "cracked-core": RelicHooks(on_combat_start=cracked_core_on_combat_start),
    "divine-right": RelicHooks(on_combat_start=divine_right_on_combat_start),
    "bound-phylactery": RelicHooks(on_player_turn_start=bound_phylactery_on_player_turn_start),
    "burning-blood": RelicHooks(on_combat_end=burning_blood_on_combat_end),
}


def resolve_relic_hooks(relic_id: str) -> RelicHooks:
    return RELIC_HOOKS.get(relic_id, RelicHooks())