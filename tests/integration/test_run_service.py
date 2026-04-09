from kill_tower.services.run_service import RunService
from kill_tower.services.save_service import SaveService


def test_run_service_advances_five_floors_and_round_trips_save(tmp_path) -> None:
    service = RunService(save_service=SaveService(base_dir=tmp_path))

    result = service.run_auto(
        character_id="ironclad",
        snapshot_tag="2026-04-09_build_unknown",
        lang="eng",
        act_id="underdocks",
        seed=7,
        floors=5,
    )

    assert result.record.floor == 5
    assert result.record.victory is True
    assert result.record.player.hp > 0
    assert [room.room_type for room in result.record.rooms] == [
        "monster",
        "monster",
        "monster",
        "event",
        "merchant",
    ]
    assert any(event.action == "combat_resolved" for event in result.replay.events)
    assert any(line.startswith("Chosen option:") for line in result.record.transcript)
    assert any("Merchant" in line for line in result.record.transcript)

    service.save_run("slot-auto", result.record, result.replay)
    loaded = service.load_run("slot-auto")

    assert loaded.floor == 5
    assert loaded.character_id == "ironclad"
    assert loaded.player.hp == result.record.player.hp


def test_silent_starter_relic_draws_additional_cards() -> None:
    service = RunService()
    bundle = service.data_service.load_bundle(snapshot_tag="2026-04-09_build_unknown", lang="eng")
    runtime = __import__("kill_tower.engine.combat", fromlist=["CombatRuntime"]).CombatRuntime(
        registry=bundle.registry,
        seed=11,
        snapshot_tag=bundle.snapshot.tag,
    )
    state = runtime.start_encounter(
        character_id="silent",
        encounter_id="toadpoles-normal",
        shuffle_draw_pile=False,
    )

    assert len(state.player.hand) == 7
    assert any("Ring of the Snake draws 2 additional cards" in line for line in state.transcript)


def test_all_characters_can_clear_three_floor_run_slice() -> None:
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

        assert result.record.floor == 5, character_id
        assert result.record.victory is True, character_id
        assert result.record.player.hp > 0, character_id


def test_fairy_in_a_bottle_prevents_lethal_damage() -> None:
    service = RunService()
    bundle = service.data_service.load_bundle(snapshot_tag="2026-04-09_build_unknown", lang="eng")
    runtime = __import__("kill_tower.engine.combat", fromlist=["CombatRuntime"]).CombatRuntime(
        registry=bundle.registry,
        seed=11,
        snapshot_tag=bundle.snapshot.tag,
    )
    player_state = runtime.build_player_state(
        character_id="ironclad",
        current_hp=5,
        max_hp=80,
        potion_ids=["fairy-in-a-bottle"],
    )
    state = runtime.start_encounter(
        character_id="ironclad",
        encounter_id="toadpoles-normal",
        shuffle_draw_pile=False,
        player_state=player_state,
    )

    runtime.attack(state.enemies[0], state.player, 99, 1, "Test Lethal")

    assert state.player.hp == 24
    assert "fairy-in-a-bottle" not in state.player.potion_ids
    assert any("Fairy in a Bottle saves" in line for line in state.transcript)