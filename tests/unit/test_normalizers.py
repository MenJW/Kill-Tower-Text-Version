from kill_tower.data.normalizers import normalize_entity


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