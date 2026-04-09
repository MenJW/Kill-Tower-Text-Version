from __future__ import annotations

from kill_tower.engine.rng import SeededRNG
from kill_tower.engine.state_models import CardInstance, CombatPhase, CombatState, PlayerState


def draw_cards(player: PlayerState, count: int, rng: SeededRNG) -> None:
    for _ in range(count):
        if not player.draw_pile and player.discard_pile:
            refreshed = list(player.discard_pile)
            rng.shuffle(refreshed)
            player.draw_pile = refreshed
            player.discard_pile.clear()
        if not player.draw_pile:
            return
        player.hand.append(player.draw_pile.pop(0))


class TurnManager:
    def __init__(self, rng: SeededRNG) -> None:
        self.rng = rng

    def begin_combat(self, state: CombatState, opening_draw: int = 5) -> None:
        state.phase = CombatPhase.PLAYER
        state.turn = 1
        state.transcript.append("Combat started.")
        self.start_player_turn(state, cards_to_draw=opening_draw)

    def start_player_turn(self, state: CombatState, cards_to_draw: int = 5) -> None:
        state.phase = CombatPhase.PLAYER
        state.player.energy = state.player.max_energy
        draw_cards(state.player, cards_to_draw, self.rng)
        state.transcript.append(f"Turn {state.turn}: player turn started.")

    def end_player_turn(self, state: CombatState) -> None:
        state.player.discard_pile.extend(state.player.hand)
        state.player.hand.clear()
        state.phase = CombatPhase.ENEMY
        state.transcript.append(f"Turn {state.turn}: player turn ended.")

    def advance_enemy_turn(self, state: CombatState) -> None:
        for enemy in state.enemies:
            if enemy.alive:
                state.transcript.append(
                    f"Enemy {enemy.name} resolves intent {enemy.intent or 'unknown'}."
                )
        state.turn += 1
        self.start_player_turn(state)


def make_basic_draw_pile(card_ids: list[str], default_cost: int = 1) -> list[CardInstance]:
    return [
        CardInstance(definition_id=card_id, instance_id=f"{card_id}-{index}", cost=default_cost)
        for index, card_id in enumerate(card_ids, start=1)
    ]