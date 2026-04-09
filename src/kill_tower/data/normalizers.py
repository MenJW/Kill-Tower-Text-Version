from __future__ import annotations

from collections import defaultdict
from typing import Any

from kill_tower.data.event_outcomes import parse_event_outcomes
from kill_tower.utils.ids import slugify_id
from kill_tower.utils.text import collapse_whitespace, normalize_text_block

SCRIPTED_ENDPOINTS = {"cards", "relics", "potions", "enchantments", "monsters", "events"}
CHARACTER_COLORS = {"ironclad", "silent", "defect", "necrobinder", "regent"}


def get_source_id(record: dict[str, Any]) -> str:
    return str(record.get("id") or record.get("source_id") or record.get("name") or "unknown")


def build_language_index(records_by_lang: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    index: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for lang, payload in records_by_lang.items():
        if not isinstance(payload, list):
            continue
        for record in payload:
            if not isinstance(record, dict):
                continue
            source_id = get_source_id(record)
            index[source_id][lang] = record
    return dict(index)


def choose_base_record(records_by_lang: dict[str, dict[str, Any]], preferred_lang: str) -> dict[str, Any]:
    for lang in (preferred_lang, "eng", "zhs"):
        if lang in records_by_lang:
            return records_by_lang[lang]
    return next(iter(records_by_lang.values()))


def _clean_name(value: str | None, fallback: str) -> str:
    return collapse_whitespace(value or fallback)


def _clean_description(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    return normalize_text_block(str(value))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _make_reference(entity_type: str, source_id: Any) -> dict[str, str]:
    source = str(source_id)
    return {
        "entity_type": entity_type,
        "entity_id": slugify_id(source),
        "source_id": source,
    }


def _make_references(entity_type: str, source_ids: Any) -> list[dict[str, str]]:
    return [_make_reference(entity_type, source_id) for source_id in _as_list(source_ids)]


def _slug_list(values: Any) -> list[str]:
    return [slugify_id(str(value)) for value in _as_list(values)]


def _build_texts(records_by_lang: dict[str, dict[str, Any]], source_id: str) -> dict[str, dict[str, str | None]]:
    texts: dict[str, dict[str, str | None]] = {}
    for lang, record in records_by_lang.items():
        texts[lang] = {
            "name": _clean_name(record.get("name"), source_id),
            "description": _clean_description(record.get("description")),
        }
    return texts


def _make_common_record(
    endpoint: str,
    source_id: str,
    base: dict[str, Any],
    records_by_lang: dict[str, dict[str, Any]],
    snapshot_tag: str,
    base_url: str,
) -> dict[str, Any]:
    normalized = dict(base)
    normalized["id"] = slugify_id(source_id)
    normalized["source_id"] = source_id
    normalized["name"] = _clean_name(base.get("name"), source_id)
    normalized["description"] = _clean_description(base.get("description"))
    normalized["texts"] = _build_texts(records_by_lang, source_id)
    normalized["tags"] = _as_list(base.get("tags"))
    normalized["scripted"] = endpoint in SCRIPTED_ENDPOINTS
    normalized["implemented"] = False
    normalized["source_meta"] = {
        "source_name": "spire_codex",
        "source_url": f"{base_url.rstrip('/')}/api/{endpoint}",
        "endpoint": endpoint,
        "snapshot_tag": snapshot_tag,
    }
    normalized["localized_payloads"] = records_by_lang
    normalized["image_url"] = base.get("image_url")
    normalized["beta_image_url"] = base.get("beta_image_url")
    return normalized


def _character_id_from_color(color: str | None) -> str | None:
    if not color:
        return None
    lowered = slugify_id(color)
    return lowered if lowered in CHARACTER_COLORS else None


def _normalize_character(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["max_hp"] = _safe_int(base.get("starting_hp")) or 0
    normalized["starting_gold"] = _safe_int(base.get("starting_gold")) or 0
    normalized["starting_energy"] = _safe_int(base.get("max_energy")) or 3
    normalized["color"] = base.get("color")
    normalized["starter_relics"] = _make_references("relic", base.get("starting_relics"))
    normalized["starter_deck"] = _make_references("card", base.get("starting_deck"))
    return normalized


def _normalize_card(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    color = base.get("color")
    vars_payload = base.get("vars") or {}
    magic = None
    if isinstance(vars_payload, dict):
        for key, value in vars_payload.items():
            if isinstance(value, int) and key not in {"Damage", "Block", "Repeat"}:
                magic = value
                break

    normalized["color"] = color
    normalized["character_id"] = _character_id_from_color(color)
    normalized["rarity"] = base.get("rarity_key") or base.get("rarity")
    normalized["card_type"] = base.get("type_key") or base.get("type")
    normalized["target"] = base.get("target")
    normalized["keywords"] = _slug_list(base.get("keywords_key") or base.get("keywords"))
    normalized["numbers"] = {
        "cost": _safe_int(base.get("cost")),
        "damage": _safe_int(base.get("damage")),
        "block": _safe_int(base.get("block")),
        "magic": magic,
    }
    return normalized


def _normalize_relic(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["rarity"] = base.get("rarity_key") or base.get("rarity")
    normalized["pool"] = base.get("pool")
    normalized["keywords"] = _slug_list(base.get("keywords_key") or base.get("keywords"))
    return normalized


def _normalize_potion(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["rarity"] = base.get("rarity_key") or base.get("rarity")
    normalized["pool"] = base.get("pool")
    normalized["target"] = base.get("target")
    return normalized


def _normalize_enchantment(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["card_type"] = base.get("card_type")
    normalized["applicable_to"] = base.get("applicable_to")
    normalized["extra_card_text"] = _clean_description(base.get("extra_card_text"))
    normalized["is_stackable"] = bool(base.get("is_stackable"))
    return normalized


def _normalize_power(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["power_type"] = base.get("type")
    normalized["stack_type"] = base.get("stack_type")
    return normalized


def _normalize_monster_move(raw_move: dict[str, Any]) -> dict[str, Any]:
    raw_damage = raw_move.get("damage")
    damage = _safe_int(raw_damage)
    ascension_damage = None
    hit_count = None
    if isinstance(raw_damage, dict):
        damage = _safe_int(raw_damage.get("normal"))
        ascension_damage = _safe_int(raw_damage.get("ascension"))
        hit_count = _safe_int(raw_damage.get("hit_count"))

    return {
        "id": slugify_id(str(raw_move.get("id") or raw_move.get("name") or "move")),
        "name": raw_move.get("name"),
        "intent": raw_move.get("intent") or "Unknown",
        "damage": damage,
        "ascension_damage": ascension_damage,
        "hits": hit_count,
        "block": _safe_int(raw_move.get("block")),
        "heal": _safe_int(raw_move.get("heal")),
        "powers": _as_list(raw_move.get("powers")),
        "description": raw_move.get("name"),
    }


def _normalize_monster(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["monster_type"] = base.get("type")
    normalized["hp_min"] = _safe_int(base.get("min_hp"))
    normalized["hp_max"] = _safe_int(base.get("max_hp"))
    normalized["moves"] = [
        _normalize_monster_move(move)
        for move in _as_list(base.get("moves"))
        if isinstance(move, dict)
    ]
    normalized["encounters"] = [
        _make_reference("encounter", encounter.get("encounter_id"))
        for encounter in _as_list(base.get("encounters"))
        if isinstance(encounter, dict) and encounter.get("encounter_id")
    ]
    return normalized


def _normalize_event_option(raw_option: dict[str, Any]) -> dict[str, Any]:
    description = _clean_description(raw_option.get("description"))
    return {
        "id": slugify_id(str(raw_option.get("id") or raw_option.get("title") or "option")),
        "label": _clean_name(raw_option.get("title"), str(raw_option.get("id") or "Option")),
        "description": description,
        "requirement": None,
        "outcomes": parse_event_outcomes(description),
    }


def _normalize_event_page(raw_page: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": slugify_id(str(raw_page.get("id") or "page")),
        "body": _clean_description(raw_page.get("description")) or "",
        "choices": [
            _normalize_event_option(option)
            for option in _as_list(raw_page.get("options"))
            if isinstance(option, dict)
        ],
    }


def _normalize_event(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["event_type"] = base.get("type")
    act = base.get("act")
    normalized["acts"] = [slugify_id(str(act))] if act else []
    pages: list[dict[str, Any]] = []
    root_options = [
        _normalize_event_option(option)
        for option in _as_list(base.get("options"))
        if isinstance(option, dict)
    ]
    root_body = _clean_description(base.get("description"))
    if root_body or root_options:
        pages.append({"id": "root", "body": root_body or "", "choices": root_options})
    pages.extend(
        _normalize_event_page(page)
        for page in _as_list(base.get("pages"))
        if isinstance(page, dict)
    )
    normalized["pages"] = pages
    return normalized


def _normalize_encounter(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    act = base.get("act")
    normalized["act"] = slugify_id(str(act)) if act else None
    normalized["room_type"] = base.get("room_type")
    normalized["monsters"] = [
        _make_reference("monster", monster.get("id"))
        for monster in _as_list(base.get("monsters"))
        if isinstance(monster, dict) and monster.get("id")
    ]
    return normalized


def _normalize_act(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["num_rooms"] = _safe_int(base.get("num_rooms"))
    normalized["bosses"] = _make_references("encounter", base.get("bosses"))
    normalized["ancients"] = [slugify_id(str(ancient)) for ancient in _as_list(base.get("ancients"))]
    normalized["events"] = _make_references("event", base.get("events"))
    normalized["encounters"] = _make_references("encounter", base.get("encounters"))
    return normalized


def _normalize_ascension(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["level"] = _safe_int(base.get("level")) or 0
    return normalized


def _normalize_achievement(normalized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    normalized["category"] = base.get("category")
    normalized["character"] = slugify_id(str(base.get("character"))) if base.get("character") else None
    normalized["threshold"] = _safe_int(base.get("threshold"))
    normalized["condition"] = _clean_description(base.get("condition"))
    return normalized


NORMALIZER_MAP = {
    "characters": _normalize_character,
    "cards": _normalize_card,
    "relics": _normalize_relic,
    "potions": _normalize_potion,
    "enchantments": _normalize_enchantment,
    "powers": _normalize_power,
    "monsters": _normalize_monster,
    "events": _normalize_event,
    "encounters": _normalize_encounter,
    "acts": _normalize_act,
    "ascensions": _normalize_ascension,
    "achievements": _normalize_achievement,
}


def normalize_entity(
    endpoint: str,
    records_by_lang: dict[str, dict[str, Any]],
    preferred_lang: str,
    snapshot_tag: str,
    base_url: str,
) -> dict[str, Any]:
    base = choose_base_record(records_by_lang, preferred_lang)
    source_id = get_source_id(base)
    normalized = _make_common_record(endpoint, source_id, base, records_by_lang, snapshot_tag, base_url)
    normalizer = NORMALIZER_MAP.get(endpoint)
    if normalizer is not None:
        normalized = normalizer(normalized, base)
    return normalized


def sort_normalized_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _sort_key(record: dict[str, Any]) -> tuple[int, str]:
        order = record.get("compendium_order")
        return (order if isinstance(order, int) else 1_000_000, str(record.get("id", "")))

    return sorted(records, key=_sort_key)