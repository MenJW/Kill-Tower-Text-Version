from pathlib import Path

from kill_tower.data.registry import build_registry
from kill_tower.data.validators import validate_registry


def test_registry_loads_real_snapshot_without_validation_issues() -> None:
    normalized_dir = Path("data/normalized/2026-04-09_build_unknown/zhs")

    registry = build_registry(normalized_dir)
    issues = validate_registry(registry)

    assert registry.summary()["characters"] == 5
    assert registry.summary()["cards"] == 576
    assert registry.summary()["relics"] == 288
    assert registry.summary()["events"] == 66
    assert registry.characters["defect"].texts["eng"].name == "The Defect"
    assert registry.characters["defect"].texts["zhs"].name == "故障机器人"
    assert registry.events["abyssal-baths"].pages
    assert issues == []