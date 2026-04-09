from kill_tower.data.service import DataService


def test_data_service_loads_latest_snapshot_registry() -> None:
    service = DataService()

    snapshot = service.select_snapshot()
    registry = service.load_registry(lang="zhs")

    assert snapshot.tag == "2026-04-09_build_unknown"
    assert registry.characters["defect"].texts["eng"].name == "The Defect"
    assert registry.characters["defect"].texts["zhs"].name == "故障机器人"


def test_data_service_loads_requested_snapshot_and_language() -> None:
    service = DataService()
    registry = service.load_registry(snapshot_tag="2026-04-09_build_unknown", lang="eng")

    assert registry.summary()["cards"] == 576
    assert registry.summary()["events"] == 66