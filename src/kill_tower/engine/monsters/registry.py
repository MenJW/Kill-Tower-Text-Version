from __future__ import annotations

from typing import TYPE_CHECKING

from kill_tower.data.schemas import MonsterMove
from kill_tower.engine.state_models import MonsterState

if TYPE_CHECKING:
    from kill_tower.engine.combat.runtime import CombatRuntime


def get_current_move(runtime: "CombatRuntime", monster: MonsterState) -> MonsterMove | None:
    definition = runtime.get_monster_definition(monster)
    if not definition.moves:
        return None
    return definition.moves[monster.move_cursor % len(definition.moves)]


def preview_next_intent(runtime: "CombatRuntime", monster: MonsterState) -> MonsterMove | None:
    move = get_current_move(runtime, monster)
    if move is None:
        monster.current_move_id = None
        monster.intent = None
        return None
    monster.current_move_id = move.id
    monster.intent = move.intent
    return move


def execute_monster_turn(runtime: "CombatRuntime", monster: MonsterState) -> MonsterMove | None:
    move = get_current_move(runtime, monster)
    if move is None:
        runtime.log(f"{monster.name} has no move definition.")
        return None
    runtime.execute_monster_move(monster, move)
    monster.move_history.append(move.id)
    monster.move_cursor += 1
    preview_next_intent(runtime, monster)
    return move