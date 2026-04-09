from __future__ import annotations

from typing import TYPE_CHECKING

from kill_tower.engine.state_models import CardInstance, MonsterState

if TYPE_CHECKING:
    from kill_tower.engine.combat.runtime import CombatRuntime


def _require_target(runtime: "CombatRuntime", target: MonsterState | None, card_name: str) -> MonsterState:
    if target is None:
        raise ValueError(f"Card {card_name} requires a target.")
    return target


def strike_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    enemy = _require_target(runtime, target, definition.name or card.definition_id)
    runtime.attack(
        attacker=runtime.state.player,
        target=enemy,
        base_damage=definition.numbers.damage or 0,
        hits=1,
        source_name=definition.name or "Strike",
    )


def defend_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    runtime.gain_block(
        target=runtime.state.player,
        amount=definition.numbers.block or 0,
        source_name=definition.name or "Defend",
    )


def bash_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    enemy = _require_target(runtime, target, definition.name or card.definition_id)
    runtime.attack(
        attacker=runtime.state.player,
        target=enemy,
        base_damage=definition.numbers.damage or 0,
        hits=1,
        source_name=definition.name or "Bash",
    )
    if enemy.alive:
        runtime.apply_power(
            target=enemy,
            power_id="vulnerable",
            amount=definition.numbers.magic or 0,
            source_name=definition.name or "Bash",
        )


def unsupported_card_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    runtime.log(f"{definition.name or card.definition_id} has no executable script yet.")