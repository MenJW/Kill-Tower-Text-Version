from __future__ import annotations

import re
from typing import TYPE_CHECKING

from kill_tower.data.event_outcomes import strip_markup
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
    runtime.gain_resource(
        resource_id="star",
        amount=definition.numbers.magic or 0,
        source_name=definition.name or "Venerate",
    )


def zap_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    runtime.channel_orb("lightning-orb", definition.name or "Zap")


def dualcast_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    runtime.evoke_rightmost_orb(times=2, source_name=definition.name or "Dualcast")


def bodyguard_script(runtime: "CombatRuntime", card: CardInstance, target: MonsterState | None) -> None:
    definition = runtime.get_card_definition(card)
    runtime.gain_resource(
        resource_id="osty_hp",
        amount=definition.numbers.magic or 0,
        source_name=definition.name or "Bodyguard",
    )


def unleash_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    enemy = _require_target(runtime, target, definition.name or card.definition_id)
    summon_power = runtime.player.get_resource("osty_hp")
    runtime.attack(
        attacker=runtime.state.player,
        target=enemy,
        base_damage=(definition.numbers.damage or 0) + summon_power,
        hits=1,
        source_name=definition.name or "Unleash",
    )


def pacts_end_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    if len(runtime.player.exhaust_pile) < 3:
        runtime.log(f"{definition.name or card.definition_id} cannot be played without 3 exhausted cards.")
        return
    runtime.attack_all_enemies(
        attacker=runtime.state.player,
        base_damage=definition.numbers.damage or 0,
        hits=1,
        source_name=definition.name or "Pact's End",
    )


def squeeze_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    enemy = _require_target(runtime, target, definition.name or card.definition_id)
    prior_osty_attacks = runtime.player.get_resource("osty_attacks_played")
    runtime.attack(
        attacker=runtime.state.player,
        target=enemy,
        base_damage=(definition.numbers.damage or 0) + prior_osty_attacks * 5,
        hits=1,
        source_name=definition.name or "Squeeze",
    )
    runtime.player.add_resource("osty_attacks_played", 1)


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


_IGNORABLE_CLAUSE_PATTERNS = (
    re.compile(r"^Can only be played if\b", re.IGNORECASE),
    re.compile(r"^Costs? \d+ less\b", re.IGNORECASE),
    re.compile(r"^This card costs \d+\b", re.IGNORECASE),
    re.compile(r"^Costs? \[[a-z-]+:\d+\] less\b", re.IGNORECASE),
    re.compile(r"^Next turn\b", re.IGNORECASE),
    re.compile(r"^Retain your Hand this turn\b", re.IGNORECASE),
)

_POWER_NAME_TO_ID = {
    "vulnerable": "vulnerable",
    "weak": "weak",
    "poison": "poison",
    "doom": "doom",
    "strength": "strength",
    "dexterity": "dexterity",
    "focus": "focus",
}

_ORB_NAME_TO_ID = {
    "lightning": "lightning-orb",
    "frost": "frost-orb",
    "plasma": "plasma-orb",
}


def generic_description_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> tuple[bool, list[str]]:
    definition = runtime.get_card_definition(card)
    description = strip_markup(definition.description or "")
    if not description:
        return False, []

    applied = False
    unhandled: list[str] = []
    clauses: list[str] = []
    for sentence in re.split(r"\.\s*", description.replace("\n", ". ").strip()):
        expanded = _expand_clause(sentence)
        clauses.extend(expanded)

    for raw_clause in clauses:
        clause = raw_clause.strip(" .")
        if not clause:
            continue
        if any(pattern.search(clause) for pattern in _IGNORABLE_CLAUSE_PATTERNS):
            continue
        if _apply_clause(runtime, card, target, clause):
            applied = True
            continue
        unhandled.append(clause)

    return applied, unhandled


def _expand_clause(clause: str) -> list[str]:
    cleaned = clause.strip()
    if not cleaned:
        return []
    for separator in (" and you ", " and "):
        if separator in cleaned.lower():
            parts = re.split(separator, cleaned, flags=re.IGNORECASE)
            if len(parts) > 1 and all(_looks_like_action(part) for part in parts):
                normalized_parts: list[str] = []
                for index, part in enumerate(parts):
                    if index > 0 and separator.strip() == "and you" and not part.lower().startswith("you "):
                        part = f"You {part}"
                    normalized_parts.append(part)
                return normalized_parts
    return [cleaned]


def _looks_like_action(clause: str) -> bool:
    lowered = clause.strip().lower()
    return lowered.startswith(
        (
            "deal ",
            "gain ",
            "draw ",
            "discard ",
            "lose ",
            "channel ",
            "apply ",
            "enemy loses ",
            "all enemies lose ",
            "osty deals ",
            "you gain ",
            "exhaust ",
        )
    )


def _apply_clause(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
    clause: str,
) -> bool:
    definition = runtime.get_card_definition(card)
    enemy = target

    if match := re.fullmatch(r"(?:You )?gain (\d+) Block", clause, flags=re.IGNORECASE):
        runtime.gain_block(runtime.state.player, int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Draw (\d+) cards?", clause, flags=re.IGNORECASE):
        runtime.draw_cards_for_player(int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Discard (\d+) cards?", clause, flags=re.IGNORECASE):
        runtime.discard_cards(int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Exhaust (\d+) cards?", clause, flags=re.IGNORECASE):
        runtime.exhaust_cards(int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Exhaust the top card of your Draw Pile", clause, flags=re.IGNORECASE):
        runtime.exhaust_top_draw_pile(1, definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Exhaust ALL your (\w+) cards", clause, flags=re.IGNORECASE):
        exhausted = runtime.exhaust_cards(len(runtime.player.hand), definition.name or card.definition_id, card_type=match.group(1))
        return exhausted > 0

    if match := re.fullmatch(r"Lose (\d+) HP", clause, flags=re.IGNORECASE):
        runtime.lose_hp(runtime.state.player, int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"(?:You )?gain (\d+) energy", clause, flags=re.IGNORECASE):
        runtime.gain_energy(int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"(?:You )?gain (\d+) star", clause, flags=re.IGNORECASE):
        runtime.gain_resource("star", int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Channel (\d+) (Lightning|Frost|Plasma)", clause, flags=re.IGNORECASE):
        orb_id = _ORB_NAME_TO_ID[match.group(2).lower()]
        for _ in range(int(match.group(1))):
            runtime.channel_orb(orb_id, definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"(?:Deal|Osty deals) (\d+) damage to ALL enemies(?: (twice|(\d+) times))?", clause, flags=re.IGNORECASE):
        hits = 2 if match.group(2) == "twice" else int(match.group(3) or 1)
        runtime.attack_all_enemies(runtime.state.player, int(match.group(1)), hits, definition.name or card.definition_id)
        if clause.lower().startswith("osty deals"):
            runtime.player.add_resource("osty_attacks_played", 1)
        return True

    if match := re.fullmatch(r"(?:Deal|Osty deals) (\d+) damage", clause, flags=re.IGNORECASE):
        resolved_enemy = _require_target(runtime, enemy, definition.name or card.definition_id)
        runtime.attack(
            attacker=runtime.state.player,
            target=resolved_enemy,
            base_damage=int(match.group(1)),
            hits=1,
            source_name=definition.name or card.definition_id,
        )
        if clause.lower().startswith("osty deals"):
            runtime.player.add_resource("osty_attacks_played", 1)
        return True

    if match := re.fullmatch(r"Enemy loses (\d+) (Strength|Dexterity|Focus) this turn", clause, flags=re.IGNORECASE):
        resolved_enemy = _require_target(runtime, enemy, definition.name or card.definition_id)
        runtime.apply_temporary_power(
            resolved_enemy,
            _POWER_NAME_TO_ID[match.group(2).lower()],
            -int(match.group(1)),
            definition.name or card.definition_id,
        )
        return True

    if match := re.fullmatch(r"All enemies lose (\d+) (Strength|Dexterity|Focus) this turn", clause, flags=re.IGNORECASE):
        for resolved_enemy in runtime.alive_enemies():
            runtime.apply_temporary_power(
                resolved_enemy,
                _POWER_NAME_TO_ID[match.group(2).lower()],
                -int(match.group(1)),
                definition.name or card.definition_id,
            )
        return True

    if match := re.fullmatch(r"Apply (\d+) (Vulnerable|Weak|Poison|Doom) to ALL enemies", clause, flags=re.IGNORECASE):
        power_id = _POWER_NAME_TO_ID[match.group(2).lower()]
        for resolved_enemy in runtime.alive_enemies():
            runtime.apply_power(resolved_enemy, power_id, int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"Apply (\d+) (Vulnerable|Weak|Poison|Doom) to a random enemy", clause, flags=re.IGNORECASE):
        enemies = runtime.alive_enemies()
        if not enemies:
            return False
        resolved_enemy = runtime.rng.choice(enemies)
        runtime.apply_power(
            resolved_enemy,
            _POWER_NAME_TO_ID[match.group(2).lower()],
            int(match.group(1)),
            definition.name or card.definition_id,
        )
        return True

    if match := re.fullmatch(r"Apply (\d+) (Vulnerable|Weak|Poison|Doom)", clause, flags=re.IGNORECASE):
        resolved_enemy = _require_target(runtime, enemy, definition.name or card.definition_id)
        runtime.apply_power(
            resolved_enemy,
            _POWER_NAME_TO_ID[match.group(2).lower()],
            int(match.group(1)),
            definition.name or card.definition_id,
        )
        return True

    if match := re.fullmatch(r"(?:You )?gain (\d+) (Strength|Dexterity|Focus) this turn", clause, flags=re.IGNORECASE):
        runtime.apply_temporary_power(
            runtime.state.player,
            _POWER_NAME_TO_ID[match.group(2).lower()],
            int(match.group(1)),
            definition.name or card.definition_id,
        )
        return True

    if match := re.fullmatch(r"Whenever you are attacked this turn, deal (\d+) damage back", clause, flags=re.IGNORECASE):
        runtime.apply_temporary_power(runtime.state.player, "thorns", int(match.group(1)), definition.name or card.definition_id)
        return True

    if match := re.fullmatch(r"(?:You )?gain (\d+) (Strength|Dexterity|Focus)", clause, flags=re.IGNORECASE):
        runtime.apply_power(
            runtime.state.player,
            _POWER_NAME_TO_ID[match.group(2).lower()],
            int(match.group(1)),
            definition.name or card.definition_id,
        )
        return True

    if match := re.fullmatch(
        r"If you have played fewer than (\d+) cards this turn, draw (\d+) cards?",
        clause,
        flags=re.IGNORECASE,
    ):
        if len(runtime.state.cards_played_this_turn) < int(match.group(1)):
            runtime.draw_cards_for_player(int(match.group(2)), definition.name or card.definition_id)
        return True

    return False


def unsupported_card_script(
    runtime: "CombatRuntime",
    card: CardInstance,
    target: MonsterState | None,
) -> None:
    definition = runtime.get_card_definition(card)
    applied, unhandled_clauses = generic_description_script(runtime, card, target)
    if applied and not unhandled_clauses:
        return
    if applied:
        runtime.log(
            f"{definition.name or card.definition_id} still has unimplemented clauses: "
            + "; ".join(unhandled_clauses)
        )
        return
    if generic_numbers_script(runtime, card, target):
        runtime.log(f"{definition.name or card.definition_id} used number-only fallback resolution.")
        return
    runtime.log(f"{definition.name or card.definition_id} has no executable script yet.")