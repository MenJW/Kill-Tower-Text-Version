from kill_tower.services.save_service import SaveService


def test_save_service_round_trip(tmp_path) -> None:
    service = SaveService(base_dir=tmp_path)
    payload = {"snapshot_tag": "test", "floor": 7}

    service.save_run("slot-1", payload)

    assert service.load_run("slot-1") == payload
    assert service.list_slots() == ["slot-1"]