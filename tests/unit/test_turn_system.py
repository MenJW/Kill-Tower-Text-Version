from kill_tower.engine.rng import SeededRNG
from kill_tower.engine.state_models import CombatState, MonsterState, PlayerState
from kill_tower.engine.turn_system import TurnManager, make_basic_draw_pile


def test_begin_combat_draws_opening_hand() -> None:
    player = PlayerState(
        combatant_id="ironclad",
        name="Ironclad",
        max_hp=80,
        hp=80,
        draw_pile=make_basic_draw_pile(["strike", "defend", "bash"]),
    )
    enemy = MonsterState(combatant_id="slime", name="Slime", max_hp=10, hp=10, intent="attack")
    state = CombatState(seed=1, player=player, enemies=[enemy])

    TurnManager(SeededRNG(1)).begin_combat(state, opening_draw=2)

    assert len(state.player.hand) == 2
    assert state.transcript[0] == "Combat started."


def test_end_and_advance_turn_moves_hand_to_discard() -> None:
    player = PlayerState(
        combatant_id="ironclad",
        name="Ironclad",
        max_hp=80,
        hp=80,
        draw_pile=make_basic_draw_pile(["strike", "defend", "bash"]),
    )
    enemy = MonsterState(combatant_id="slime", name="Slime", max_hp=10, hp=10, intent="attack")
    state = CombatState(seed=2, player=player, enemies=[enemy])
    manager = TurnManager(SeededRNG(2))

    manager.begin_combat(state, opening_draw=1)
    manager.end_player_turn(state)
    manager.advance_enemy_turn(state)

    assert state.turn == 2
    assert len(state.player.hand) == 3
    assert len(state.player.discard_pile) == 0
    assert state.player.energy == state.player.max_energy