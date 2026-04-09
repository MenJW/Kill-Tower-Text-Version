from kill_tower.data.service import DataService
from kill_tower.engine.combat import CombatRuntime


def test_ironclad_vertical_slice_wins_toadpoles_encounter() -> None:
    service = DataService()
    registry = service.load_registry(snapshot_tag="2026-04-09_build_unknown", lang="eng")
    runtime = CombatRuntime(registry=registry, seed=7, snapshot_tag="2026-04-09_build_unknown")

    result = runtime.run_vertical_slice(
        character_id="ironclad",
        encounter_id="toadpoles-normal",
        max_turns=12,
        shuffle_draw_pile=False,
    )

    assert result.victory is True
    assert result.player_hp > 0
    assert any("Burning Blood heals" in line for line in result.transcript)
    assert any("Combat won." in line for line in result.transcript)