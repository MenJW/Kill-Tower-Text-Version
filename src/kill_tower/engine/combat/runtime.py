from __future__ import annotations

from dataclasses import dataclass

from kill_tower.data.registry import ContentRegistry
from kill_tower.data.schemas import CardDefinition, CharacterDefinition, MonsterDefinition, MonsterMove
from kill_tower.engine.cards import resolve_card_script
from kill_tower.engine.monsters import execute_monster_turn, preview_next_intent
from kill_tower.engine.relics import resolve_relic_hooks
from kill_tower.engine.rng import SeededRNG
from kill_tower.engine.state_models import CardInstance, CombatPhase, CombatState, MonsterState, PlayerState
from kill_tower.engine.turn_system import TurnManager
from kill_tower.utils.ids import slugify_id


@dataclass(slots=True)
class VerticalSliceResult:
    snapshot_tag: str | None
    encounter_id: str
    character_id: str
    victory: bool
    turns: int
    player_hp: int
    max_player_hp: int
    transcript: list[str]


class CombatRuntime:
    def __init__(
        self,
        registry: ContentRegistry,
        seed: int = 0,
        snapshot_tag: str | None = None,
    ) -> None:
        self.registry = registry
        self.snapshot_tag = snapshot_tag
        self.rng = SeededRNG(seed)
        self.turn_manager = TurnManager(self.rng)
        self.state: CombatState | None = None

    def run_vertical_slice(
        self,
        character_id: str = "ironclad",
        encounter_id: str = "toadpoles-normal",
        max_turns: int = 12,
        shuffle_draw_pile: bool = True,
    ) -> VerticalSliceResult:
        self.start_encounter(
            character_id=character_id,
            encounter_id=encounter_id,
            shuffle_draw_pile=shuffle_draw_pile,
        )
        while self.state.victory is None and self.state.turn <= max_turns:
            self.play_auto_turn()
            if self.state.victory is not None:
                break
            self.run_enemy_turn()
        if self.state.victory is None:
            self.state.victory = False
            self.log("Combat ended because the turn limit was reached.")
        return VerticalSliceResult(
            snapshot_tag=self.state.snapshot_tag,
            encounter_id=encounter_id,
            character_id=character_id,
            victory=bool(self.state.victory),
            turns=self.state.turn,
            player_hp=self.state.player.hp,
            max_player_hp=self.state.player.max_hp,
            transcript=list(self.state.transcript),
        )

    def start_encounter(
        self,
        character_id: str,
        encounter_id: str,
        shuffle_draw_pile: bool = True,
    ) -> CombatState:
        player = self._build_player_state(character_id)
        if shuffle_draw_pile:
            self.rng.shuffle(player.draw_pile)
        enemies = self._build_enemy_states(encounter_id)
        self.state = CombatState(
            seed=self.rng.seed,
            player=player,
            enemies=enemies,
            snapshot_tag=self.snapshot_tag,
            encounter_id=encounter_id,
        )
        for enemy in self.state.enemies:
            preview_next_intent(self, enemy)
        encounter_name = self.registry.encounters[encounter_id].name or encounter_id
        self.log(f"Encounter queued: {encounter_name}.")
        self.log(
            f"{player.name} enters combat against {', '.join(enemy.name for enemy in enemies)}."
        )
        self.turn_manager.begin_combat(self.state, opening_draw=5)
        return self.state

    @property
    def player(self) -> PlayerState:
        return self.state.player

    def get_card_definition(self, card: CardInstance | str) -> CardDefinition:
        card_id = card.definition_id if isinstance(card, CardInstance) else card
        return self.registry.cards[card_id]

    def get_monster_definition(self, monster: MonsterState | str) -> MonsterDefinition:
        monster_id = monster.definition_id if isinstance(monster, MonsterState) else monster
        if monster_id is None:
            raise KeyError("Monster definition id is missing.")
        return self.registry.monsters[monster_id]

    def log(self, message: str) -> None:
        self.state.transcript.append(message)

    def alive_enemies(self) -> list[MonsterState]:
        return [enemy for enemy in self.state.enemies if enemy.alive]

    def play_auto_turn(self) -> None:
        while self.state.phase == CombatPhase.PLAYER and self.state.victory is None:
            choice = self._choose_auto_play()
            if choice is None:
                break
            hand_index, target_index = choice
            self.play_card(hand_index, target_index)
        if self.state.victory is None:
            self._end_player_turn()

    def play_card(self, hand_index: int, target_index: int | None = None) -> None:
        card = self.player.hand.pop(hand_index)
        definition = self.get_card_definition(card)
        if card.cost > self.player.energy:
            raise ValueError(f"Card {definition.name or card.definition_id} is not affordable.")
        self.player.energy -= card.cost
        target = None
        if target_index is not None:
            targets = self.alive_enemies()
            if 0 <= target_index < len(targets):
                target = targets[target_index]
        self.log(
            f"{self.player.name} plays {definition.name or card.definition_id} "
            f"for {card.cost} energy."
        )
        resolve_card_script(definition.id)(self, card, target)
        self.player.discard_pile.append(card)
        self._check_combat_end()

    def run_enemy_turn(self) -> None:
        if self.state.victory is not None:
            return
        self.state.phase = CombatPhase.ENEMY
        for enemy in self.alive_enemies():
            enemy.block = 0
            move = execute_monster_turn(self, enemy)
            self._apply_end_of_turn_effects(enemy)
            if move is not None:
                self.log(f"Next intent for {enemy.name}: {enemy.intent or 'Unknown'}.")
            if self._check_combat_end():
                return
        self.state.turn += 1
        self.turn_manager.start_player_turn(self.state)

    def attack(
        self,
        attacker: PlayerState | MonsterState,
        target: PlayerState | MonsterState,
        base_damage: int,
        hits: int = 1,
        source_name: str = "Attack",
    ) -> int:
        total_hp_damage = 0
        strength = attacker.get_power("strength")
        vulnerable_multiplier = 1.5 if target.get_power("vulnerable") > 0 else 1.0
        per_hit_damage = max(0, int((base_damage + strength) * vulnerable_multiplier))
        actual_hits = max(1, hits)
        for _ in range(actual_hits):
            hp_damage = self._apply_raw_damage(target, per_hit_damage)
            total_hp_damage += hp_damage
            if not target.alive:
                break
        self.log(
            f"{attacker.name} uses {source_name} on {target.name} for {per_hit_damage} damage"
            f" x{actual_hits} ({total_hp_damage} HP lost)."
        )
        if attacker is self.player and target.get_power("thorns") > 0 and target.alive:
            thorns = target.get_power("thorns")
            reflected = 0
            for _ in range(actual_hits):
                reflected += self._apply_raw_damage(attacker, thorns)
            self.log(f"{target.name}'s Thorns deals {reflected} damage back to {attacker.name}.")
        if not target.alive:
            self.log(f"{target.name} is defeated.")
        return total_hp_damage

    def gain_block(
        self,
        target: PlayerState | MonsterState,
        amount: int,
        source_name: str,
    ) -> None:
        if amount <= 0:
            return
        target.block += amount
        self.log(f"{target.name} gains {amount} Block from {source_name}.")

    def heal(
        self,
        target: PlayerState | MonsterState,
        amount: int,
        source_name: str,
    ) -> None:
        if amount <= 0:
            return
        previous_hp = target.hp
        target.hp = min(target.max_hp, target.hp + amount)
        healed = target.hp - previous_hp
        if healed > 0:
            self.log(f"{target.name} heals {healed} HP from {source_name}.")

    def apply_power(
        self,
        target: PlayerState | MonsterState,
        power_id: str,
        amount: int,
        source_name: str,
    ) -> None:
        normalized_power = slugify_id(power_id)
        if amount == 0:
            return
        target.add_power(normalized_power, amount)
        self.log(f"{target.name} gains {amount} {normalized_power} from {source_name}.")

    def execute_monster_move(self, monster: MonsterState, move: MonsterMove) -> None:
        self.log(f"{monster.name} uses {move.name or move.id}.")
        if move.block:
            self.gain_block(monster, move.block, move.name or move.id)
        if move.damage is not None:
            self.attack(
                attacker=monster,
                target=self.player,
                base_damage=move.damage,
                hits=move.hits or 1,
                source_name=move.name or move.id,
            )
        if move.heal:
            self.heal(monster, move.heal, move.name or move.id)
        for power_payload in move.powers:
            amount = int(power_payload.get("amount") or 0)
            target_name = str(power_payload.get("target") or "self").lower()
            power_id = str(power_payload.get("power_id") or power_payload.get("power") or "")
            target = monster if target_name == "self" else self.player
            self.apply_power(target, power_id, amount, move.name or move.id)

    def _apply_raw_damage(self, target: PlayerState | MonsterState, amount: int) -> int:
        damage = max(0, amount)
        if target.block > 0:
            absorbed = min(target.block, damage)
            target.block -= absorbed
            damage -= absorbed
        if damage > 0:
            target.hp = max(0, target.hp - damage)
        return damage

    def _build_player_state(self, character_id: str) -> PlayerState:
        character = self.registry.characters[character_id]
        draw_pile = []
        for index, card_ref in enumerate(character.starter_deck, start=1):
            definition = self.registry.cards[card_ref.entity_id]
            draw_pile.append(
                CardInstance(
                    definition_id=definition.id,
                    instance_id=f"{definition.id}-{index}",
                    cost=definition.numbers.cost or 0,
                    name=definition.name,
                    card_type=definition.card_type,
                )
            )
        return PlayerState(
            combatant_id="player",
            character_id=character.id,
            name=character.name or character_id,
            max_hp=character.max_hp,
            hp=character.max_hp,
            energy=character.starting_energy,
            max_energy=character.starting_energy,
            gold=character.starting_gold,
            draw_pile=draw_pile,
            relic_ids=[ref.entity_id for ref in character.starter_relics],
        )

    def _build_enemy_states(self, encounter_id: str) -> list[MonsterState]:
        encounter = self.registry.encounters[encounter_id]
        enemies: list[MonsterState] = []
        for index, monster_ref in enumerate(encounter.monsters, start=1):
            definition = self.registry.monsters[monster_ref.entity_id]
            hp = definition.hp_min or definition.hp_max or 1
            enemies.append(
                MonsterState(
                    combatant_id=f"{definition.id}-{index}",
                    definition_id=definition.id,
                    name=definition.name or definition.id,
                    max_hp=hp,
                    hp=hp,
                )
            )
        return enemies

    def _choose_auto_play(self) -> tuple[int, int | None] | None:
        playable: list[tuple[int, CardInstance, CardDefinition]] = []
        for index, card in enumerate(self.player.hand):
            definition = self.get_card_definition(card)
            if card.cost <= self.player.energy:
                playable.append((index, card, definition))
        if not playable:
            return None

        enemies = self.alive_enemies()
        if not enemies:
            return None

        for index, card, definition in sorted(
            playable,
            key=lambda item: (self._estimated_card_damage(item[2], enemies[0]), -item[0]),
            reverse=True,
        ):
            if definition.numbers.damage is None:
                continue
            for target_index, enemy in enumerate(sorted(enemies, key=lambda item: item.hp)):
                if self._estimated_card_damage(definition, enemy) >= enemy.hp:
                    actual_target_index = self.alive_enemies().index(enemy)
                    return index, actual_target_index

        for index, card, definition in playable:
            if definition.id == "bash":
                targets = sorted(self.alive_enemies(), key=self._enemy_threat, reverse=True)
                target = targets[0]
                return index, self.alive_enemies().index(target)

        incoming_damage = self._estimated_incoming_damage()
        if incoming_damage > self.player.block:
            for index, card, definition in playable:
                if definition.id == "defend-ironclad":
                    return index, None

        attack_cards = [
            (index, definition) for index, _card, definition in playable if definition.numbers.damage is not None
        ]
        if attack_cards:
            target = max(self.alive_enemies(), key=self._enemy_threat)
            index, definition = max(
                attack_cards,
                key=lambda item: self._estimated_card_damage(item[1], target),
            )
            return index, self.alive_enemies().index(target)

        for index, _card, definition in playable:
            if definition.id == "defend-ironclad":
                return index, None
        return None

    def _end_player_turn(self) -> None:
        self.turn_manager.end_player_turn(self.state)
        self._apply_end_of_turn_effects(self.player)

    def _apply_end_of_turn_effects(self, actor: PlayerState | MonsterState) -> None:
        ritual = actor.get_power("ritual")
        if ritual > 0:
            actor.add_power("strength", ritual)
            self.log(f"{actor.name} gains {ritual} Strength from ritual.")
        if actor.get_power("vulnerable") > 0:
            actor.reduce_power("vulnerable", 1)
            self.log(f"{actor.name}'s vulnerable decreases to {actor.get_power('vulnerable')}.")

    def _estimated_card_damage(self, definition: CardDefinition, target: MonsterState) -> int:
        if definition.numbers.damage is None:
            return 0
        damage = definition.numbers.damage + self.player.get_power("strength")
        if target.get_power("vulnerable") > 0:
            damage = int(damage * 1.5)
        return max(0, damage)

    def _estimated_incoming_damage(self) -> int:
        total = 0
        for enemy in self.alive_enemies():
            definition = self.get_monster_definition(enemy)
            if not definition.moves:
                continue
            move = definition.moves[enemy.move_cursor % len(definition.moves)]
            if move.damage is None:
                continue
            damage = move.damage + enemy.get_power("strength")
            total += damage * (move.hits or 1)
        return total

    def _enemy_threat(self, enemy: MonsterState) -> tuple[int, int]:
        definition = self.get_monster_definition(enemy)
        move = definition.moves[enemy.move_cursor % len(definition.moves)] if definition.moves else None
        damage = 0 if move is None or move.damage is None else move.damage * (move.hits or 1)
        return (damage, -enemy.hp)

    def _check_combat_end(self) -> bool:
        if not self.player.alive:
            self.state.victory = False
            self.log(f"{self.player.name} has fallen.")
            return True
        if any(enemy.alive for enemy in self.state.enemies):
            return False
        self.state.victory = True
        self.log("Combat won.")
        for relic_id in self.player.relic_ids:
            hooks = resolve_relic_hooks(relic_id)
            if hooks.on_combat_end is not None:
                hooks.on_combat_end(self)
        return True