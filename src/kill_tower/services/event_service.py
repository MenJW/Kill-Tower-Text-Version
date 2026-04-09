from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from kill_tower.data.schemas import EventChoice, EventDefinition, EventOutcome, EventPage

if TYPE_CHECKING:
    from kill_tower.data.registry import ContentRegistry


@dataclass(slots=True)
class EventResolution:
    event_id: str
    visited_pages: list[str] = field(default_factory=list)
    chosen_options: list[str] = field(default_factory=list)
    applied_outcomes: list[str] = field(default_factory=list)
    transcript: list[str] = field(default_factory=list)


class EventService:
    def __init__(self, registry: "ContentRegistry") -> None:
        self.registry = registry

    def resolve_auto(self, event_id: str, player_state: Any, max_steps: int = 5) -> EventResolution:
        event = self.registry.events[event_id]
        resolution = EventResolution(event_id=event.id)
        if not event.pages:
            resolution.transcript.append(f"Event {event.name or event.id} has no structured pages.")
            return resolution

        page = event.pages[0]
        steps = 0
        while steps < max_steps and page is not None:
            resolution.visited_pages.append(page.id)
            if page.body:
                resolution.transcript.append(page.body)
            if not page.choices:
                break

            choice = self._choose_best_choice(page.choices, player_state)
            resolution.chosen_options.append(choice.id)
            resolution.transcript.append(f"Chosen option: {choice.label}.")
            resolution.applied_outcomes.extend(self._apply_outcomes(choice.outcomes, player_state))
            next_page = self._find_followup_page(event, choice.id, visited_pages=set(resolution.visited_pages))
            if next_page is None:
                break
            page = next_page
            steps += 1
        return resolution

    def _choose_best_choice(self, choices: list[EventChoice], player_state: Any) -> EventChoice:
        return max(choices, key=lambda choice: (self._score_choice(choice, player_state), choice.id))

    def _score_choice(self, choice: EventChoice, player_state: Any) -> float:
        score = 0.0
        description = (choice.description or "").lower()
        if "locked" in choice.id or "requires" in description or "you don't have" in description:
            return -10_000
        missing_hp = max(0, getattr(player_state, "max_hp", 0) - getattr(player_state, "hp", 0))
        for outcome in choice.outcomes:
            value = self._coerce_numeric_value(outcome.value)
            count = self._outcome_count(outcome.value)
            if outcome.outcome_type == "gain_max_hp":
                score += value * 2.0
            elif outcome.outcome_type == "heal":
                score += min(value, missing_hp)
            elif outcome.outcome_type == "take_damage":
                if value >= getattr(player_state, "hp", 0):
                    score -= 1_000
                score -= value * 1.0
            elif outcome.outcome_type == "gain_gold":
                score += value * 0.2
            elif outcome.outcome_type == "lose_gold":
                score -= value * 0.2
            elif outcome.outcome_type == "obtain_relic":
                score += 25
            elif outcome.outcome_type == "obtain_random_relic":
                score += 20 * count
            elif outcome.outcome_type == "obtain_card":
                score += 8
            elif outcome.outcome_type == "obtain_random_card":
                score += 7 * count
            elif outcome.outcome_type == "obtain_potion":
                score += 6
            elif outcome.outcome_type == "obtain_random_potion":
                score += 5 * count
            elif outcome.outcome_type == "remove_card":
                score += 10 * count
            elif outcome.outcome_type == "upgrade_card":
                score += 7 * count
            elif outcome.outcome_type == "transform_card":
                score += 8 * count
            elif outcome.outcome_type == "trade_relic":
                score += 12 * count
            elif outcome.outcome_type == "downgrade_card":
                score -= 4 * count
            elif outcome.outcome_type == "unsupported":
                score -= 1
        return score

    def _apply_outcomes(self, outcomes: list[EventOutcome], player_state: Any) -> list[str]:
        messages: list[str] = []
        for outcome in outcomes:
            outcome_type = outcome.outcome_type
            value = outcome.value
            if outcome_type == "gain_max_hp" and isinstance(value, int):
                player_state.max_hp += value
                player_state.hp += value
                messages.append(f"Gain {value} Max HP.")
            elif outcome_type == "lose_max_hp" and isinstance(value, int):
                player_state.max_hp = max(1, player_state.max_hp - value)
                player_state.hp = min(player_state.hp, player_state.max_hp)
                messages.append(f"Lose {value} Max HP.")
            elif outcome_type == "heal" and isinstance(value, int):
                previous_hp = player_state.hp
                player_state.hp = min(player_state.max_hp, player_state.hp + value)
                messages.append(f"Heal {player_state.hp - previous_hp} HP.")
            elif outcome_type == "take_damage" and isinstance(value, int):
                player_state.hp = max(0, player_state.hp - value)
                messages.append(f"Take {value} damage.")
            elif outcome_type == "gain_gold" and isinstance(value, int):
                player_state.gold += value
                messages.append(f"Gain {value} gold.")
            elif outcome_type == "lose_gold" and isinstance(value, int):
                actual = min(player_state.gold, value)
                player_state.gold -= actual
                messages.append(f"Lose {actual} gold.")
            elif outcome_type == "remove_card":
                count = self._outcome_count(value)
                removed = self._remove_cards(player_state, count)
                if removed:
                    messages.append(f"Remove {', '.join(removed)} from the deck.")
            elif outcome_type == "upgrade_card":
                count = self._outcome_count(value)
                selected = self._preview_deck_cards(player_state, count)
                if selected:
                    messages.append(f"Upgrade {', '.join(selected)}.")
            elif outcome_type == "downgrade_card":
                count = self._outcome_count(value)
                selected = self._preview_deck_cards(player_state, count)
                if selected:
                    messages.append(f"Downgrade {', '.join(selected)}.")
            elif outcome_type == "transform_card":
                count = self._outcome_count(value)
                transformed = self._transform_cards(player_state, count)
                messages.extend(transformed)
            elif outcome_type == "trade_relic":
                traded = self._trade_relic(player_state, outcome)
                messages.extend(traded)
            elif outcome_type == "obtain_random_card":
                obtained = self._obtain_random_cards(player_state, outcome)
                messages.extend(obtained)
            elif outcome_type == "obtain_random_relic":
                obtained = self._obtain_random_relics(player_state, outcome)
                messages.extend(obtained)
            elif outcome_type == "obtain_random_potion":
                obtained = self._obtain_random_potions(player_state, outcome)
                messages.extend(obtained)
            elif outcome_type in {"obtain_relic", "obtain_card", "obtain_potion"} and outcome.reference is not None:
                entity_id = outcome.reference.entity_id
                count = self._outcome_count(value)
                if outcome_type == "obtain_relic":
                    if entity_id not in player_state.relic_ids:
                        player_state.relic_ids.append(entity_id)
                    messages.append(f"Obtain relic {entity_id}.")
                elif outcome_type == "obtain_card":
                    for _ in range(count):
                        player_state.deck_definition_ids.append(entity_id)
                    messages.append(f"Obtain card {entity_id} x{count}.")
                elif hasattr(player_state, "potion_ids"):
                    available = max(0, getattr(player_state, "max_potion_slots", 3) - len(player_state.potion_ids))
                    actual = min(count, available)
                    for _ in range(actual):
                        player_state.potion_ids.append(entity_id)
                    if actual > 0:
                        messages.append(f"Obtain potion {entity_id} x{actual}.")
            elif outcome_type == "enchant_card" and outcome.reference is not None:
                messages.append(f"Enchant a card with {outcome.reference.entity_id}.")
            elif outcome_type == "divine" and isinstance(value, int):
                messages.append(f"Divine {value} time(s).")
            elif outcome_type == "unsupported" and isinstance(value, str):
                messages.append(f"Unsupported event effect: {value}")
        return messages

    def _remove_basic_card(self, player_state: Any) -> str | None:
        priorities = ["strike", "defend"]
        for prefix in priorities:
            for index, card_id in enumerate(player_state.deck_definition_ids):
                if card_id.startswith(prefix):
                    return player_state.deck_definition_ids.pop(index)
        if player_state.deck_definition_ids:
            return player_state.deck_definition_ids.pop(0)
        return None

    def _remove_cards(self, player_state: Any, count: int) -> list[str]:
        removed: list[str] = []
        for _ in range(max(1, count)):
            card_id = self._remove_basic_card(player_state)
            if card_id is None:
                break
            removed.append(card_id)
        return removed

    def _preview_deck_cards(self, player_state: Any, count: int) -> list[str]:
        if not getattr(player_state, "deck_definition_ids", None):
            return []
        ranked = sorted(player_state.deck_definition_ids, key=lambda card_id: (card_id.startswith("strike"), card_id.startswith("defend"), card_id))
        return ranked[: max(1, count)]

    def _transform_cards(self, player_state: Any, count: int) -> list[str]:
        messages: list[str] = []
        removed = self._remove_cards(player_state, count)
        for _removed_card in removed:
            candidates = self._candidate_cards(player_state, {})
            if not candidates:
                continue
            card_id = candidates[0].id
            player_state.deck_definition_ids.append(card_id)
            messages.append(f"Transform into {card_id}.")
        return messages

    def _trade_relic(self, player_state: Any, outcome: EventOutcome) -> list[str]:
        if not getattr(player_state, "relic_ids", None):
            return []
        removed_relic = player_state.relic_ids.pop(0)
        messages = [f"Trade away relic {removed_relic}."]
        messages.extend(self._obtain_random_relics(player_state, outcome))
        return messages

    def _obtain_random_cards(self, player_state: Any, outcome: EventOutcome) -> list[str]:
        payload = self._outcome_payload(outcome.value)
        count = self._outcome_count(outcome.value)
        candidates = self._candidate_cards(player_state, payload)
        messages: list[str] = []
        for card in candidates[:count]:
            player_state.deck_definition_ids.append(card.id)
            messages.append(f"Obtain card {card.id}.")
        return messages

    def _obtain_random_relics(self, player_state: Any, outcome: EventOutcome) -> list[str]:
        payload = self._outcome_payload(outcome.value)
        count = self._outcome_count(outcome.value)
        candidates = self._candidate_relics(player_state, payload)
        messages: list[str] = []
        for relic in candidates[:count]:
            if relic.id in player_state.relic_ids:
                continue
            player_state.relic_ids.append(relic.id)
            messages.append(f"Obtain relic {relic.id}.")
        return messages

    def _obtain_random_potions(self, player_state: Any, outcome: EventOutcome) -> list[str]:
        payload = self._outcome_payload(outcome.value)
        count = self._outcome_count(outcome.value)
        candidates = self._candidate_potions(player_state, payload)
        available = max(0, getattr(player_state, "max_potion_slots", 3) - len(player_state.potion_ids))
        messages: list[str] = []
        for potion in candidates[: min(count, available)]:
            player_state.potion_ids.append(potion.id)
            messages.append(f"Obtain potion {potion.id}.")
        return messages

    def _candidate_cards(self, player_state: Any, payload: dict[str, Any]) -> list[Any]:
        character_id = payload.get("character_id") or getattr(player_state, "character_id", None)
        card_type = payload.get("card_type")
        cost = payload.get("cost")
        candidates = [
            card
            for card in self.registry.cards.values()
            if (character_id is None or card.character_id == character_id)
            and (card_type is None or card.card_type == card_type)
            and (cost is None or card.numbers.cost == cost)
        ]
        ranked = sorted(
            candidates,
            key=lambda card: (float(card.numbers.damage or 0) + float(card.numbers.block or 0), card.rarity == "Rare", card.id),
            reverse=True,
        )
        return ranked

    def _candidate_relics(self, player_state: Any, payload: dict[str, Any]) -> list[Any]:
        tag = str(payload.get("tag") or "").lower()
        candidates = []
        for relic in self.registry.relics.values():
            if relic.id in getattr(player_state, "relic_ids", []):
                continue
            haystack = " ".join(filter(None, [relic.id, relic.name or "", relic.description or ""])).lower()
            if tag and tag not in haystack:
                continue
            candidates.append(relic)
        return sorted(candidates, key=lambda relic: (relic.rarity == "Rare", relic.id), reverse=True)

    def _candidate_potions(self, player_state: Any, payload: dict[str, Any]) -> list[Any]:
        rarity = payload.get("rarity")
        candidates = [
            potion
            for potion in self.registry.potions.values()
            if potion.id not in getattr(player_state, "potion_ids", [])
            and (rarity is None or potion.rarity == rarity)
        ]
        return sorted(candidates, key=lambda potion: (potion.rarity == "Rare", potion.id), reverse=True)

    def _coerce_numeric_value(self, value: Any) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, dict):
            return int(value.get("count", 0))
        return 0

    def _outcome_count(self, value: Any) -> int:
        if isinstance(value, dict):
            return int(value.get("count", 1))
        if isinstance(value, (int, float)):
            return int(value)
        return 1

    def _outcome_payload(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    def _find_followup_page(
        self,
        event: EventDefinition,
        choice_id: str,
        visited_pages: set[str],
    ) -> EventPage | None:
        for page in event.pages:
            if page.id == choice_id and page.id not in visited_pages:
                return page
        for page in event.pages:
            if page.id.startswith(choice_id) and page.id not in visited_pages:
                return page
        return None