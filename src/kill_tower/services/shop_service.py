from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kill_tower.data.registry import ContentRegistry
from kill_tower.services.ascension_service import AscensionRules
from kill_tower.services.reward_service import RewardService


@dataclass(slots=True)
class MerchantOffer:
    remove_cost: int
    removable_card_id: str | None
    card_offer_id: str | None
    card_price: int | None
    potion_offer_id: str | None
    potion_price: int | None


class ShopService:
    def __init__(self, reward_service: RewardService | None = None) -> None:
        self.reward_service = reward_service or RewardService()

    def preview_merchant(
        self,
        player_state: Any,
        character_id: str,
        registry: ContentRegistry,
        seed: int,
        floor: int,
        ascension_rules: AscensionRules,
        cards_removed: int,
    ) -> MerchantOffer:
        card_offer = self.reward_service._choose_card_reward(
            player_state,
            character_id,
            registry,
            seed + 31,
            floor,
            ascension_rules,
        )
        potion_offer = self.reward_service._choose_potion_reward(
            player_state,
            character_id,
            registry,
            seed + 79,
            floor,
            room_type="merchant",
        )
        return MerchantOffer(
            remove_cost=75 + cards_removed * 25,
            removable_card_id=self._preview_basic_card(player_state),
            card_offer_id=card_offer.id if card_offer is not None else None,
            card_price=None if card_offer is None else (55 if card_offer.rarity == "Common" else 75),
            potion_offer_id=potion_offer.id if potion_offer is not None else None,
            potion_price=60 if potion_offer is not None else None,
        )

    def purchase_removal(self, player_state: Any, cards_removed: int) -> tuple[str | None, int]:
        remove_cost = 75 + cards_removed * 25
        if player_state.gold < remove_cost:
            return None, cards_removed
        removed_card = self._remove_basic_card(player_state)
        if removed_card is None:
            return None, cards_removed
        player_state.gold -= remove_cost
        return f"Merchant removes {removed_card} for {remove_cost} gold.", cards_removed + 1

    def purchase_card(self, player_state: Any, offer: MerchantOffer) -> str | None:
        if offer.card_offer_id is None or offer.card_price is None or player_state.gold < offer.card_price:
            return None
        player_state.gold -= offer.card_price
        player_state.deck_definition_ids.append(offer.card_offer_id)
        purchased_card = offer.card_offer_id
        purchased_price = offer.card_price
        offer.card_offer_id = None
        offer.card_price = None
        return f"Merchant sells {purchased_card} for {purchased_price} gold."

    def purchase_potion(self, player_state: Any, offer: MerchantOffer) -> str | None:
        if offer.potion_offer_id is None or offer.potion_price is None or player_state.gold < offer.potion_price:
            return None
        if len(player_state.potion_ids) >= getattr(player_state, "max_potion_slots", 3):
            return None
        player_state.gold -= offer.potion_price
        player_state.potion_ids.append(offer.potion_offer_id)
        purchased_potion = offer.potion_offer_id
        purchased_price = offer.potion_price
        offer.potion_offer_id = None
        offer.potion_price = None
        return f"Merchant sells {purchased_potion} for {purchased_price} gold."

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

        removal_message, removed_count = self.purchase_removal(player_state, removed_count)
        if removal_message is not None:
            messages.append(removal_message)

        offer = self.preview_merchant(
            player_state,
            character_id,
            registry,
            seed,
            floor,
            ascension_rules,
            removed_count,
        )
        card_message = self.purchase_card(player_state, offer)
        if card_message is not None:
            messages.append(card_message)

        potion_message = self.purchase_potion(player_state, offer)
        if potion_message is not None:
            messages.append(potion_message)

        return messages, removed_count

    def _preview_basic_card(self, player_state: Any) -> str | None:
        for prefix in ("strike", "defend"):
            for card_id in player_state.deck_definition_ids:
                if card_id.startswith(prefix):
                    return card_id
        return player_state.deck_definition_ids[0] if player_state.deck_definition_ids else None

    def _remove_basic_card(self, player_state: Any) -> str | None:
        for prefix in ("strike", "defend"):
            for index, card_id in enumerate(player_state.deck_definition_ids):
                if card_id.startswith(prefix):
                    return player_state.deck_definition_ids.pop(index)
        if player_state.deck_definition_ids:
            return player_state.deck_definition_ids.pop(0)
        return None