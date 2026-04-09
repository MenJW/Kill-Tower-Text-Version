from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kill_tower.engine.monsters import __doc__ as _
from kill_tower.engine.rng import SeededRNG
from kill_tower.engine.state_models import CombatState, MonsterState, PlayerState
from kill_tower.engine.turn_system import TurnManager, make_basic_draw_pile


def main() -> None:
    player = PlayerState(
        combatant_id="ironclad",
        name="Ironclad",
        max_hp=80,
        hp=80,
        draw_pile=make_basic_draw_pile(["strike", "defend", "bash"]),
    )
    enemy = MonsterState(combatant_id="slime-small", name="Small Slime", max_hp=12, hp=12, intent="attack")
    state = CombatState(seed=7, player=player, enemies=[enemy])
    turn_manager = TurnManager(SeededRNG(state.seed))
    turn_manager.begin_combat(state, opening_draw=2)
    turn_manager.end_player_turn(state)
    turn_manager.advance_enemy_turn(state)
    print("\n".join(state.transcript))


if __name__ == "__main__":
    main()