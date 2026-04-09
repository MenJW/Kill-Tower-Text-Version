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
_LEADING_COUNT_RE = re.compile(r"^(?P<count>\d+)\s+", re.IGNORECASE)
_TRAILING_ITEM_TYPE_RE = re.compile(r"\s+(?:relics?|cards?|potions?)$", re.IGNORECASE)


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
        (r"\bGain (\d+)(?:-(\d+))? Max HP\b", "gain_max_hp"),
        (r"\bLose (\d+)(?:-(\d+))? Max HP\b", "lose_max_hp"),
        (r"\bHeal (\d+)(?:-(\d+))? HP\b", "heal"),
        (r"\bTake (\d+)(?:-(\d+))? damage\b", "take_damage"),
        (r"\bLose (\d+)(?:-(\d+))? HP\b", "take_damage"),
        (r"\bGain (\d+)(?:-(\d+))? gold\b", "gain_gold"),
        (r"\bLose (\d+)(?:-(\d+))? gold\b", "lose_gold"),
        (r"\bPay (\d+)(?:-(\d+))? gold\b", "lose_gold"),
        (r"\bGain (\d+)(?:-(\d+))? Block\b", "gain_block"),
        (r"\bGain (\d+)(?:-(\d+))? star\b", "gain_star"),
        (r"获得(\d+)(?:-(\d+))?点最大生命", "gain_max_hp"),
        (r"失去(\d+)(?:-(\d+))?点最大生命", "lose_max_hp"),
        (r"恢复(\d+)(?:-(\d+))?点生命", "heal"),
        (r"受到(\d+)(?:-(\d+))?点伤害", "take_damage"),
        (r"失去(\d+)(?:-(\d+))?点生命", "take_damage"),
        (r"获得(\d+)(?:-(\d+))?金币", "gain_gold"),
        (r"失去(\d+)(?:-(\d+))?金币", "lose_gold"),
        (r"支付(\d+)(?:-(\d+))?金币", "lose_gold"),
        (r"获得(\d+)(?:-(\d+))?点格挡", "gain_block"),
    ]
    for pattern, outcome_type in numeric_patterns:
        for match in re.finditer(pattern, cleaned, flags=re.IGNORECASE):
            add(outcome_type, _range_midpoint(match.group(1), match.group(2)))

    simple_patterns = [
        (r"\bRemove a card\b", "remove_card"),
        (r"\bObtain a card\b", "obtain_card"),
        (r"\bObtain a potion\b", "obtain_potion"),
        (r"\bFight\b", "start_combat"),
        (r"\bCombat\b", "start_combat"),
        (r"移除1张牌", "remove_card"),
        (r"获得1张牌", "obtain_card"),
        (r"获得1瓶药水", "obtain_potion"),
        (r"战斗", "start_combat"),
    ]
    for pattern, outcome_type in simple_patterns:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            add(outcome_type)

    if match := re.search(r"\bRemove (\d+) cards? from your Deck\b", cleaned, re.IGNORECASE):
        add("remove_card", int(match.group(1)))
    elif match := re.search(r"从你的牌组中(?:选择)?(\d+)张牌移除", cleaned, re.IGNORECASE):
        add("remove_card", int(match.group(1)))
    elif re.search(r"\bRemove a card(?: from your Deck)?\b", cleaned, re.IGNORECASE):
        add("remove_card", 1)
    elif re.search(r"从你的牌组中(?:选择)?1张牌移除", cleaned, re.IGNORECASE):
        add("remove_card", 1)

    if match := re.search(r"\bUpgrade (\d+) random cards?\b", cleaned, re.IGNORECASE):
        add("upgrade_card", {"count": int(match.group(1)), "random": True})
    elif match := re.search(r"随机升级(\d+)张牌", cleaned, re.IGNORECASE):
        add("upgrade_card", {"count": int(match.group(1)), "random": True})
    elif re.search(r"\bUpgrade a random card(?: in your Deck)?\b", cleaned, re.IGNORECASE):
        add("upgrade_card", {"count": 1, "random": True})
    elif re.search(r"随机升级1张牌", cleaned, re.IGNORECASE):
        add("upgrade_card", {"count": 1, "random": True})
    elif re.search(r"\bUpgrade a card(?: in your Deck)?\b", cleaned, re.IGNORECASE):
        add("upgrade_card", {"count": 1})
    elif re.search(r"升级1张牌", cleaned, re.IGNORECASE):
        add("upgrade_card", {"count": 1})

    if match := re.search(r"\bDowngrade (\d+) random cards?\b", cleaned, re.IGNORECASE):
        add("downgrade_card", {"count": int(match.group(1)), "random": True})

    if match := re.search(r"\bTransform (\d+) cards?(?: in your Deck)?\b", cleaned, re.IGNORECASE):
        add("transform_card", {"count": int(match.group(1))})
    elif match := re.search(r"转化(\d+)张牌", cleaned, re.IGNORECASE):
        add("transform_card", {"count": int(match.group(1))})
    elif re.search(r"\bTransform a card(?: in your Deck)?\b", cleaned, re.IGNORECASE):
        add("transform_card", {"count": 1})
    elif re.search(r"转化1张牌", cleaned, re.IGNORECASE):
        add("transform_card", {"count": 1})

    if match := re.search(r"\bObtain (\d+) (Ironclad|Silent|Defect|Regent|Necrobinder) cards\b", cleaned, re.IGNORECASE):
        add(
            "obtain_random_card",
            {"count": int(match.group(1)), "character_id": slugify(match.group(2))},
        )
    elif match := re.search(r"\bChoose (\d+) of (\d+) random cards to add to your Deck\b", cleaned, re.IGNORECASE):
        add(
            "obtain_random_card",
            {"count": int(match.group(1)), "choices": int(match.group(2))},
        )
    elif re.search(r"\bObtain a random Power\b", cleaned, re.IGNORECASE):
        add("obtain_random_card", {"count": 1, "card_type": "Power"})
    elif re.search(r"\bObtain a random 0 cost card\b", cleaned, re.IGNORECASE):
        add("obtain_random_card", {"count": 1, "cost": 0})

    if match := re.search(r"\bObtain (\d+) random Relics\b", cleaned, re.IGNORECASE):
        add("obtain_random_relic", {"count": int(match.group(1))})
    elif re.search(r"\b(?:Obtain|Receive) a random Relic\b", cleaned, re.IGNORECASE):
        add("obtain_random_relic", {"count": 1})
    elif re.search(r"\bObtain a random Doll Relic\b", cleaned, re.IGNORECASE):
        add("obtain_random_relic", {"count": 1, "tag": "doll"})
    elif match := re.search(r"\bChoose (\d+) of (\d+) Doll Relics\b", cleaned, re.IGNORECASE):
        add(
            "obtain_random_relic",
            {"count": int(match.group(1)), "choices": int(match.group(2)), "tag": "doll"},
        )
    elif re.search(r"\bTrade one of your Relics for a random Relic\b", cleaned, re.IGNORECASE):
        add("trade_relic", {"count": 1})

    if match := re.search(r"\bProcure (\d+) random (Common|Uncommon|Rare) Potion\b", cleaned, re.IGNORECASE):
        add(
            "obtain_random_potion",
            {"count": int(match.group(1)), "rarity": match.group(2).title()},
        )
    elif match := re.search(r"\bProcure (\d+) random (Common|Uncommon|Rare) Potions\b", cleaned, re.IGNORECASE):
        add(
            "obtain_random_potion",
            {"count": int(match.group(1)), "rarity": match.group(2).title()},
        )

    if match := re.search(r"\bDivine (\d+) times\b", cleaned, re.IGNORECASE):
        add("divine", int(match.group(1)))

    if registry is not None and (enchantment_reference := _match_enchantment_reference(cleaned, registry)) is not None:
        add("enchant_card", {"count": 1}, enchantment_reference)

    if registry is not None:
        item_reference, item_count = _match_item_reference(cleaned, registry)
        if item_reference is not None:
            add(f"obtain_{item_reference['entity_type']}", item_count, item_reference)

    if not outcomes and cleaned:
        lowered = cleaned.lower()
        if "requires" in lowered or "you don't have" in lowered or "out of gold" in lowered:
            return outcomes
        if any(keyword in lowered for keyword in ["upgrade", "transform", "random", "procure", "relic", "deck"]) or len(cleaned) <= 80:
            add("unsupported", cleaned)
    return outcomes


def slugify(value: str) -> str:
    return collapse_whitespace(value).lower().replace(" ", "-")


def _range_midpoint(start: str, end: str | None) -> int:
    first = int(start)
    if end is None:
        return first
    second = int(end)
    return (first + second) // 2


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


def _match_item_reference(cleaned_description: str, registry: "ContentRegistry") -> tuple[dict[str, str] | None, int]:
    patterns = [
        r"\b(?:Obtain|Receive|Get|Procure)\s+(.+?)(?:\.|$)",
        r"\bAdd\s+(.+?)\s+to your Deck\b",
        r"\bGain\s+(.+?)(?:\.|$)",
    ]
    for pattern in patterns:
        obtain_match = re.search(pattern, cleaned_description, re.IGNORECASE)
        if obtain_match is None:
            continue
        candidate, count = _normalize_item_name(obtain_match.group(1))
        if not candidate:
            continue
        for entity_type, collection in (
            ("relic", registry.relics),
            ("card", registry.cards),
            ("potion", registry.potions),
        ):
            for entity in collection.values():
                for text in entity.texts.values():
                    normalized_name, _ = _normalize_item_name(text.name)
                    if normalized_name == candidate:
                        return (
                            {
                                "entity_type": entity_type,
                                "entity_id": entity.id,
                                "source_id": entity.source_id,
                            },
                            count,
                        )
    return None, 1


def _match_enchantment_reference(cleaned_description: str, registry: "ContentRegistry") -> dict[str, str] | None:
    enchant_match = re.search(r"\bEnchant a card(?: that [^.]+)? with (.+?)(?:\.|$)", cleaned_description, re.IGNORECASE)
    if enchant_match is None:
        return None
    candidate, _ = _normalize_item_name(enchant_match.group(1))
    if not candidate:
        return None
    for enchantment in registry.enchantments.values():
        for text in enchantment.texts.values():
            normalized_name, _ = _normalize_item_name(text.name)
            if normalized_name == candidate:
                return {
                    "entity_type": "enchantment",
                    "entity_id": enchantment.id,
                    "source_id": enchantment.source_id,
                }
    return None


def _normalize_item_name(value: str | None) -> tuple[str, int]:
    if not value:
        return "", 1
    cleaned = strip_markup(value)
    cleaned = re.sub(r"\b(?:random|common|uncommon|rare)\b", "", cleaned, flags=re.IGNORECASE)
    count = 1
    count_match = _LEADING_COUNT_RE.match(cleaned)
    if count_match is not None:
        count = int(count_match.group("count"))
        cleaned = cleaned[count_match.end() :]
    cleaned = _LEADING_ARTICLE_RE.sub("", cleaned)
    cleaned = _TRAILING_ITEM_TYPE_RE.sub("", cleaned)
    cleaned = cleaned.strip(" .!")
    if not cleaned or cleaned[0].isdigit() or "choose" in cleaned.lower() or "divine" in cleaned.lower():
        return "", count
    return cleaned.lower(), count