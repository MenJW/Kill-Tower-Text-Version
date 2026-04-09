from __future__ import annotations

from typing import Any

from kill_tower.data.registry import ContentRegistry
from kill_tower.services.ascension_service import AscensionRules
from kill_tower.services.reward_service import RewardService


class ShopService:
    def __init__(self, reward_service: RewardService | None = None) -> None:
        self.reward_service = reward_service or RewardService()

    def resolve_merchant(
        self,
        player_state: Any,
        character_id: str,
        registry: ContentRegistry,
        seed: int,
        floor: int,
        ascension_rules: AscensionRules,
        cards_removed: int,
    ) -> tuple[list[str], int]:
        messages: list[str] = [f"Merchant visited with {player_state.gold} gold."]
        removed_count = cards_removed

        remove_cost = 75 + cards_removed * 25
        removed_card = None
        if player_state.gold >= remove_cost:
            removed_card = self._remove_basic_card(player_state)
            if removed_card is not None:
                player_state.gold -= remove_cost
                removed_count += 1
                messages.append(f"Merchant removes {removed_card} for {remove_cost} gold.")

        card_offer = self.reward_service._choose_card_reward(
            player_state,
            character_id,
            registry,
            seed + 31,
            floor,
            ascension_rules,
        )
        if card_offer is not None:
            card_price = 55 if card_offer.rarity == "Common" else 75
            if player_state.gold >= card_price:
                player_state.gold -= card_price
                player_state.deck_definition_ids.append(card_offer.id)
                messages.append(f"Merchant sells {card_offer.id} for {card_price} gold.")

        potion_offer = self.reward_service._choose_potion_reward(
            player_state,
            character_id,
            registry,
            seed + 79,
            floor,
            room_type="merchant",
        )
        if potion_offer is not None:
            potion_price = 60
            if player_state.gold >= potion_price and len(player_state.potion_ids) < player_state.max_potion_slots:
                player_state.gold -= potion_price
                player_state.potion_ids.append(potion_offer.id)
                messages.append(f"Merchant sells {potion_offer.id} for {potion_price} gold.")

        return messages, removed_count

    def _remove_basic_card(self, player_state: Any) -> str | None:
        for prefix in ("strike", "defend"):
            for index, card_id in enumerate(player_state.deck_definition_ids):
                if card_id.startswith(prefix):
                    return player_state.deck_definition_ids.pop(index)
        return None