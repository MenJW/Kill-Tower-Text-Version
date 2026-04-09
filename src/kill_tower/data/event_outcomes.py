from __future__ import annotations

import re
from typing import TYPE_CHECKING

from kill_tower.data.schemas import EventChoice, EventDefinition, EventOutcome
from kill_tower.utils.text import collapse_whitespace

if TYPE_CHECKING:
    from kill_tower.data.registry import ContentRegistry


_VALUE_TAG_RE = re.compile(r"\[(?P<name>[a-z-]+):(?P<value>-?\d+)\]", re.IGNORECASE)
_MARKUP_TAG_RE = re.compile(r"\[/?[^\]]+\]")
_LEADING_ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
_TRAILING_ITEM_TYPE_RE = re.compile(r"\s+(?:relic|card|potion)$", re.IGNORECASE)


def strip_markup(text: str) -> str:
    rendered = _VALUE_TAG_RE.sub(
        lambda match: f"{match.group('value')} {match.group('name').replace('-', ' ')}",
        text,
    )
    rendered = _MARKUP_TAG_RE.sub("", rendered)
    rendered = rendered.replace("\n", " ")
    return collapse_whitespace(rendered)


def parse_event_outcomes(
    description: str | None,
    registry: "ContentRegistry | None" = None,
) -> list[dict[str, object]]:
    if not description:
        return []

    cleaned = strip_markup(description)
    if not cleaned:
        return []

    outcomes: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    def add(outcome_type: str, value: object = None, reference: dict[str, str] | None = None) -> None:
        key = (outcome_type, str(value) if value is not None else "")
        if key in seen:
            return
        seen.add(key)
        payload: dict[str, object] = {"outcome_type": outcome_type}
        if value is not None:
            payload["value"] = value
        if reference is not None:
            payload["reference"] = reference
        outcomes.append(payload)

    numeric_patterns = [
        (r"\bGain (\d+) Max HP\b", "gain_max_hp"),
        (r"\bLose (\d+) Max HP\b", "lose_max_hp"),
        (r"\bHeal (\d+) HP\b", "heal"),
        (r"\bTake (\d+) damage\b", "take_damage"),
        (r"\bLose (\d+) HP\b", "take_damage"),
        (r"\bGain (\d+) gold\b", "gain_gold"),
        (r"\bLose (\d+) gold\b", "lose_gold"),
        (r"\bPay (\d+) gold\b", "lose_gold"),
        (r"\bGain (\d+) Block\b", "gain_block"),
        (r"\bGain (\d+) star\b", "gain_star"),
    ]
    for pattern, outcome_type in numeric_patterns:
        for match in re.finditer(pattern, cleaned, flags=re.IGNORECASE):
            add(outcome_type, int(match.group(1)))

    simple_patterns = [
        (r"\bRemove a card\b", "remove_card"),
        (r"\bObtain a card\b", "obtain_card"),
        (r"\bObtain a potion\b", "obtain_potion"),
        (r"\bFight\b", "start_combat"),
        (r"\bCombat\b", "start_combat"),
    ]
    for pattern, outcome_type in simple_patterns:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            add(outcome_type)

    if registry is not None:
        item_reference = _match_item_reference(cleaned, registry)
        if item_reference is not None:
            add(f"obtain_{item_reference['entity_type']}", 1, item_reference)

    if not outcomes and cleaned:
        if any(keyword in cleaned.lower() for keyword in ["upgrade", "transform", "random"]) or len(cleaned) <= 80:
            add("unsupported", cleaned)
    return outcomes


def enrich_event_choice_outcomes(
    choice: EventChoice,
    registry: "ContentRegistry | None" = None,
) -> None:
    if choice.outcomes:
        return
    choice.outcomes = [
        EventOutcome.model_validate(payload)
        for payload in parse_event_outcomes(choice.description, registry=registry)
    ]


def enrich_event_definition(event: EventDefinition, registry: "ContentRegistry | None" = None) -> None:
    for page in event.pages:
        for choice in page.choices:
            enrich_event_choice_outcomes(choice, registry=registry)


def enrich_registry_events(registry: "ContentRegistry") -> None:
    for event in registry.events.values():
        enrich_event_definition(event, registry=registry)


def _match_item_reference(cleaned_description: str, registry: "ContentRegistry") -> dict[str, str] | None:
    obtain_match = re.search(r"\b(?:Obtain|Receive|Get)\s+(.+?)(?:\.|$)", cleaned_description, re.IGNORECASE)
    if obtain_match is None:
        return None
    candidate = _normalize_item_name(obtain_match.group(1))
    if not candidate:
        return None
    for entity_type, collection in (
        ("relic", registry.relics),
        ("card", registry.cards),
        ("potion", registry.potions),
    ):
        for entity in collection.values():
            for text in entity.texts.values():
                if _normalize_item_name(text.name) == candidate:
                    return {
                        "entity_type": entity_type,
                        "entity_id": entity.id,
                        "source_id": entity.source_id,
                    }
    return None


def _normalize_item_name(value: str | None) -> str:
    if not value:
        return ""
    cleaned = strip_markup(value)
    cleaned = _LEADING_ARTICLE_RE.sub("", cleaned)
    cleaned = _TRAILING_ITEM_TYPE_RE.sub("", cleaned)
    return cleaned.strip(" .!").lower()