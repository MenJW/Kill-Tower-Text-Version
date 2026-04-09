from kill_tower.services.coverage_service import CoverageService


def test_zhs_execution_coverage_matches_eng() -> None:
    service = CoverageService()
    eng = service.generate_language_report("2026-04-09_build_unknown", "eng")
    zhs = service.generate_language_report("2026-04-09_build_unknown", "zhs")

    for bucket_name in ("cards", "relics", "potions", "events", "monsters"):
        eng_bucket = getattr(eng, bucket_name)
        zhs_bucket = getattr(zhs, bucket_name)
        assert (
            zhs_bucket.resolved,
            zhs_bucket.partial,
            zhs_bucket.unresolved,
            zhs_bucket.error,
        ) == (
            eng_bucket.resolved,
            eng_bucket.partial,
            eng_bucket.unresolved,
            eng_bucket.error,
        ), bucket_name