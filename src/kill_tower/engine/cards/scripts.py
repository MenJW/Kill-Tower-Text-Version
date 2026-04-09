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


def neutralize_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    enemy = _require_target(runtime, target, definition.name or card.definition_id)
    runtime.attack(
        attacker=runtime.state.player,
        target=enemy,
        base_damage=definition.numbers.damage or 0,
        hits=1,
        source_name=definition.name or "Neutralize",
    )
    if enemy.alive:
        runtime.apply_power(
            target=enemy,
            power_id="weak",
            amount=definition.numbers.magic or 0,
            source_name=definition.name or "Neutralize",
        )


def survivor_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    runtime.gain_block(
        target=runtime.state.player,
        amount=definition.numbers.block or 0,
        source_name=definition.name or "Survivor",
    )
    if runtime.player.hand:
        discarded = runtime.player.hand.pop(0)
        runtime.player.discard_pile.append(discarded)
        discarded_name = runtime.get_card_definition(discarded).name or discarded.definition_id
        runtime.log(f"{runtime.player.name} discards {discarded_name} from Survivor.")


def falling_star_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    enemy = _require_target(runtime, target, definition.name or card.definition_id)
    runtime.attack(
        attacker=runtime.state.player,
        target=enemy,
        base_damage=definition.numbers.damage or 0,
        hits=1,
        source_name=definition.name or "Falling Star",
    )
    if enemy.alive:
        runtime.apply_power(target=enemy, power_id="weak", amount=1, source_name=definition.name or "Falling Star")
        runtime.apply_power(
            target=enemy,
            power_id="vulnerable",
            amount=1,
            source_name=definition.name or "Falling Star",
        )


def venerate_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    runtime.apply_power(
        target=runtime.state.player,
        power_id="star",
        amount=definition.numbers.magic or 0,
        source_name=definition.name or "Venerate",
    )


def generic_numbers_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> bool:
    definition = runtime.get_card_definition(card)
    applied = False
    if definition.numbers.damage is not None:
        enemy = _require_target(runtime, target, definition.name or card.definition_id)
        runtime.attack(
            attacker=runtime.state.player,
            target=enemy,
            base_damage=definition.numbers.damage,
            hits=1,
            source_name=definition.name or card.definition_id,
        )
        applied = True
    if definition.numbers.block is not None:
        runtime.gain_block(
            target=runtime.state.player,
            amount=definition.numbers.block,
            source_name=definition.name or card.definition_id,
        )
        applied = True
    return applied


def unsupported_card_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    if generic_numbers_script(runtime, card, target):
        runtime.log(
            f"{definition.name or card.definition_id} used generic fallback resolution;"
            " secondary effects are not implemented."
        )
        return
    runtime.log(f"{definition.name or card.definition_id} has no executable script yet.")