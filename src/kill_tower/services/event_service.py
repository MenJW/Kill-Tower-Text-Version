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
        missing_hp = max(0, getattr(player_state, "max_hp", 0) - getattr(player_state, "hp", 0))
        for outcome in choice.outcomes:
            value = int(outcome.value) if isinstance(outcome.value, (int, float)) else 0
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
            elif outcome.outcome_type == "obtain_card":
                score += 8
            elif outcome.outcome_type == "obtain_potion":
                score += 6
            elif outcome.outcome_type == "remove_card":
                score += 10
            elif outcome.outcome_type == "unsupported":
                score -= 1
        return score

    def _apply_outcomes(self, outcomes: list[EventOutcome], player_state: Any) -> list[str]:
        messages: list[str] = []
        for outcome in outcomes:
            outcome_type = outcome.outcome_type
            value = int(outcome.value) if isinstance(outcome.value, (int, float)) else outcome.value
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
                removed = self._remove_basic_card(player_state)
                if removed is not None:
                    messages.append(f"Remove {removed} from the deck.")
            elif outcome_type in {"obtain_relic", "obtain_card", "obtain_potion"} and outcome.reference is not None:
                entity_id = outcome.reference.entity_id
                if outcome_type == "obtain_relic":
                    if entity_id not in player_state.relic_ids:
                        player_state.relic_ids.append(entity_id)
                    messages.append(f"Obtain relic {entity_id}.")
                elif outcome_type == "obtain_card":
                    player_state.deck_definition_ids.append(entity_id)
                    messages.append(f"Obtain card {entity_id}.")
                elif hasattr(player_state, "potion_ids"):
                    player_state.potion_ids.append(entity_id)
                    messages.append(f"Obtain potion {entity_id}.")
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