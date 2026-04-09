from kill_tower.utils.ids import make_snapshot_tag, slugify_id


def test_slugify_id_normalizes_value() -> None:
    assert slugify_id(" Ironclad Strike+ ") == "ironclad-strike"


def test_make_snapshot_tag_formats_date_and_build() -> None:
    assert make_snapshot_tag("2026-03-09", "12345") == "2026-03-09_build_12345"