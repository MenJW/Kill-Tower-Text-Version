from kill_tower.data.normalizers import normalize_entity
from kill_tower.data.event_outcomes import parse_event_outcomes


def test_normalize_card_merges_texts_and_maps_fields() -> None:
    records_by_lang = {
        "eng": {
            "id": "STRIKE_DEFECT",
            "name": "Strike",
            "description": "Deal 6 damage.",
            "cost": 1,
            "type": "Attack",
            "type_key": "Attack",
            "rarity": "Basic",
            "rarity_key": "Basic",
            "target": "Enemy",
            "color": "defect",
            "damage": 6,
            "block": None,
            "keywords": [],
            "keywords_key": [],
            "vars": {"Damage": 6},
        },
        "zhs": {
            "id": "STRIKE_DEFECT",
            "name": "打击",
            "description": "造成 6 点伤害。",
            "cost": 1,
            "type": "攻击",
            "type_key": "Attack",
            "rarity": "基础",
            "rarity_key": "Basic",
            "target": "敌人",
            "color": "defect",
            "damage": 6,
            "block": None,
            "keywords": [],
            "keywords_key": [],
            "vars": {"Damage": 6},
        },
    }

    normalized = normalize_entity(
        endpoint="cards",
        records_by_lang=records_by_lang,
        preferred_lang="zhs",
        snapshot_tag="test-tag",
        base_url="https://spire-codex.com",
    )

    assert normalized["id"] == "strike-defect"
    assert normalized["source_id"] == "STRIKE_DEFECT"
    assert normalized["name"] == "打击"
    assert normalized["texts"]["eng"]["name"] == "Strike"
    assert normalized["texts"]["zhs"]["name"] == "打击"
    assert normalized["card_type"] == "Attack"
    assert normalized["character_id"] == "defect"
    assert normalized["numbers"]["damage"] == 6


def test_normalize_character_canonicalizes_starting_refs() -> None:
    records_by_lang = {
        "eng": {
            "id": "DEFECT",
            "name": "Defect",
            "description": "Robot.",
            "starting_hp": 75,
            "starting_gold": 99,
            "max_energy": 3,
            "starting_deck": ["StrikeDefect", "Dualcast"],
            "starting_relics": ["CrackedCore"],
            "color": "blue",
        },
        "zhs": {
            "id": "DEFECT",
            "name": "故障机器人",
            "description": "机器人。",
            "starting_hp": 75,
            "starting_gold": 99,
            "max_energy": 3,
            "starting_deck": ["StrikeDefect", "Dualcast"],
            "starting_relics": ["CrackedCore"],
            "color": "blue",
        },
    }

    normalized = normalize_entity(
        endpoint="characters",
        records_by_lang=records_by_lang,
        preferred_lang="eng",
        snapshot_tag="test-tag",
        base_url="https://spire-codex.com",
    )

    assert normalized["id"] == "defect"
    assert normalized["starter_deck"][0]["entity_id"] == "strike-defect"
    assert normalized["starter_relics"][0]["entity_id"] == "cracked-core"
    assert normalized["max_hp"] == 75


def test_normalize_event_option_extracts_common_outcomes() -> None:
    records_by_lang = {
        "eng": {
            "id": "ABYSSAL_BATHS",
            "name": "Abyssal Baths",
            "description": "A room with a dangerous bath.",
            "act": "Underdocks",
            "options": [
                {
                    "id": "IMMERSE",
                    "title": "Immerse",
                    "description": "Gain [green]2[/green] Max HP. Take [red]3[/red] damage.",
                },
                {
                    "id": "ABSTAIN",
                    "title": "Abstain",
                    "description": "Heal [green]10[/green] HP.",
                },
            ],
            "pages": [],
        }
    }

    normalized = normalize_entity(
        endpoint="events",
        records_by_lang=records_by_lang,
        preferred_lang="eng",
        snapshot_tag="test-tag",
        base_url="https://spire-codex.com",
    )

    root_choices = normalized["pages"][0]["choices"]
    assert root_choices[0]["outcomes"] == [
        {"outcome_type": "gain_max_hp", "value": 2},
        {"outcome_type": "take_damage", "value": 3},
    ]
    assert root_choices[1]["outcomes"] == [{"outcome_type": "heal", "value": 10}]


def test_parse_event_outcomes_extracts_structured_randomized_effects() -> None:
    outcomes = parse_event_outcomes(
        "Upgrade 2 random cards. Procure 1 random Uncommon Potion. Obtain a random Power. Remove 2 cards from your Deck."
    )

    assert outcomes == [
        {"outcome_type": "remove_card", "value": 2},
        {"outcome_type": "upgrade_card", "value": {"count": 2, "random": True}},
        {"outcome_type": "obtain_random_card", "value": {"count": 1, "card_type": "Power"}},
        {"outcome_type": "obtain_random_potion", "value": {"count": 1, "rarity": "Uncommon"}},
    ]