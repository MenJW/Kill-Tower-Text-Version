from __future__ import annotations

from typing import Any

from kill_tower.data.registry import ContentRegistry
from kill_tower.data.schemas import CardDefinition, PotionDefinition, RelicDefinition
from kill_tower.services.ascension_service import AscensionRules

SUPPORTED_SPECIAL_CARDS = {
    "bash",
    "neutralize",
    "survivor",
    "falling-star",
    "venerate",
    "zap",
    "dualcast",
    "bodyguard",
    "unleash",
}


class RewardService:
    def apply_combat_rewards(
        self,
        player_state: Any,
        character_id: str,
        registry: ContentRegistry,
        room_type: str,
        seed: int,
        floor: int,
        ascension_rules: AscensionRules,
    ) -> list[str]:
        messages: list[str] = []
        card = self._choose_card_reward(player_state, character_id, registry, seed, floor, ascension_rules)
        if card is not None:
            player_state.deck_definition_ids.append(card.id)
            messages.append(f"Reward: add {card.id} to the deck.")
        if room_type in {"elite", "boss"}:
            relic = self._choose_relic_reward(player_state, character_id, registry, seed, floor)
            if relic is not None:
                player_state.relic_ids.append(relic.id)
                messages.append(f"Reward: obtain relic {relic.id}.")
        potion = self._choose_potion_reward(player_state, character_id, registry, seed, floor, room_type)
        if potion is not None:
            player_state.potion_ids.append(potion.id)
            messages.append(f"Reward: obtain potion {potion.id}.")
        return messages

    def gold_reward(self, room_type: str, ascension_rules: AscensionRules) -> int:
        rewards = {"monster": 20, "elite": 35, "boss": 100}
        base = rewards.get(room_type, 0)
        return max(0, int(base * ascension_rules.gold_multiplier))

    def _choose_card_reward(
        self,
        player_state: Any,
        character_id: str,
        registry: ContentRegistry,
        seed: int,
        floor: int,
        ascension_rules: AscensionRules,
    ) -> CardDefinition | None:
        allowed_rarities = {"Common", "Uncommon"}
        if not ascension_rules.rare_cards_less_often:
            allowed_rarities.add("Rare")
        candidates = [
            card
            for card in registry.cards.values()
            if card.character_id == character_id
            and card.rarity in allowed_rarities
            and self._is_reward_safe_card(card)
        ]
        if not candidates:
            return None
        ranked = sorted(candidates, key=lambda card: (self._card_score(card), card.id), reverse=True)
        offset = (seed + floor) % min(len(ranked), 7)
        preview = ranked[offset : offset + 3] or ranked[:3]
        return max(preview, key=lambda card: (self._card_score(card), card.id))

    def _choose_relic_reward(
        self,
        player_state: Any,
        character_id: str,
        registry: ContentRegistry,
        seed: int,
        floor: int,
    ) -> RelicDefinition | None:
        candidates = [
            relic
            for relic in registry.relics.values()
            if relic.pool in {character_id, "shared", None}
            and relic.id not in player_state.relic_ids
            and relic.rarity != "Starter"
        ]
        if not candidates:
            return None
        ranked = sorted(candidates, key=lambda relic: (self._relic_score(relic), relic.id), reverse=True)
        return ranked[(seed + floor) % min(len(ranked), 8)]

    def _choose_potion_reward(
        self,
        player_state: Any,
        character_id: str,
        registry: ContentRegistry,
        seed: int,
        floor: int,
        room_type: str,
    ) -> PotionDefinition | None:
        if len(player_state.potion_ids) >= getattr(player_state, "max_potion_slots", 3):
            return None
        if room_type not in {"elite", "boss"} and (seed + floor) % 2 == 1:
            return None
        candidates = [
            potion
            for potion in registry.potions.values()
            if potion.pool in {character_id, "shared"}
            and potion.id not in player_state.potion_ids
        ]
        if not candidates:
            return None
        ranked = sorted(candidates, key=lambda potion: (self._potion_score(potion), potion.id), reverse=True)
        return ranked[(seed + floor) % min(len(ranked), 6)]

    def _is_reward_safe_card(self, card: CardDefinition) -> bool:
        return card.numbers.damage is not None or card.numbers.block is not None or card.id in SUPPORTED_SPECIAL_CARDS

    def _card_score(self, card: CardDefinition) -> float:
        score = float(card.numbers.damage or 0) + float(card.numbers.block or 0) * 0.9
        if card.id in SUPPORTED_SPECIAL_CARDS:
            score += 4
        if card.rarity == "Rare":
            score += 3
        elif card.rarity == "Uncommon":
            score += 1
        return score - float(card.numbers.cost or 0) * 0.2

    def _relic_score(self, relic: RelicDefinition) -> float:
        description = (relic.description or "").lower()
        score = 1.0
        for keyword, bonus in (("heal", 4), ("draw", 3), ("energy", 5), ("block", 2), ("strength", 3)):
            if keyword in description:
                score += bonus
        return score

    def _potion_score(self, potion: PotionDefinition) -> float:
        description = (potion.description or "").lower()
        score = 1.0
        for keyword, bonus in (("heal", 5), ("damage", 3), ("block", 3), ("energy", 4)):
            if keyword in description:
                score += bonus
        return score