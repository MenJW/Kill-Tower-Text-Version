from kill_tower.services.run_service import RunService


def test_five_characters_clear_five_floor_regression() -> None:
    service = RunService()

    for character_id in ["ironclad", "silent", "defect", "regent", "necrobinder"]:
        result = service.run_auto(
            character_id=character_id,
            snapshot_tag="2026-04-09_build_unknown",
            lang="eng",
            act_id="underdocks",
            seed=7,
            floors=5,
        )

        assert result.record.victory is True, character_id
        assert result.record.floor == 5, character_id
        assert len(result.record.player.deck_definition_ids) >= 11, character_id
        assert len(result.record.player.potion_ids) <= result.record.player.max_potion_slots, character_id


def test_ironclad_full_act_regression() -> None:
    service = RunService()

    result = service.run_auto(
        character_id="ironclad",
        snapshot_tag="2026-04-09_build_unknown",
        lang="eng",
        act_id="underdocks",
        seed=7,
        floors=None,
    )

    assert result.record.victory is True
    assert result.record.floor == 15
    assert result.record.player.hp > 0
    assert result.record.cards_removed >= 1
    assert len(result.record.player.deck_definition_ids) >= 15
    assert any("Completed underdocks run slice." in line for line in result.record.transcript)


def test_ascension_regression_changes_setup_and_rewards() -> None:
    service = RunService()

    asc5 = service.create_run(
        character_id="ironclad",
        snapshot_tag="2026-04-09_build_unknown",
        lang="eng",
        act_id="underdocks",
        seed=7,
        floors=7,
        ascension_level=5,
    )
    asc3 = service.run_auto(
        character_id="ironclad",
        snapshot_tag="2026-04-09_build_unknown",
        lang="eng",
        act_id="underdocks",
        seed=7,
        floors=1,
        ascension_level=3,
    )

    assert asc5.player.max_potion_slots == 2
    assert asc5.player.deck_definition_ids[-1] == "ascenders-bane"
    assert [room.room_type for room in asc5.rooms[:7]] == [
        "monster",
        "monster",
        "elite",
        "event",
        "merchant",
        "campfire",
        "elite",
    ]
    assert asc3.record.player.gold == 114