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
    assert any("Event outcomes are not yet structured" in line for line in result.record.transcript)

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