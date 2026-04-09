import json
from pathlib import Path

from kill_tower.services.run_service import RunService


UNRESOLVED_MARKERS = (
    "still has unimplemented clauses",
    "used number-only fallback resolution",
    "has no executable script yet",
    "Unsupported event effect",
)


def test_transcript_goldens_match_expected_scenarios() -> None:
    root = Path(__file__).resolve().parents[1]
    golden_dir = root / "golden" / "transcripts"
    manifest = json.loads((golden_dir / "manifest.json").read_text(encoding="utf-8"))
    service = RunService()

    for scenario in manifest["scenarios"]:
        result = service.run_auto(
            character_id=scenario["character_id"],
            snapshot_tag="2026-04-09_build_unknown",
            lang=scenario["lang"],
            act_id=scenario["act_id"],
            seed=scenario["seed"],
            floors=scenario["floors"],
        )
        transcript = "\n".join(result.record.transcript) + "\n"
        expected_transcript = (
            golden_dir / scenario["lang"] / f"{scenario['slug']}.txt"
        ).read_text(encoding="utf-8")
        expected_summary = json.loads(
            (golden_dir / scenario["lang"] / f"{scenario['slug']}.summary.json").read_text(encoding="utf-8")
        )
        actual_summary = {
            "snapshot_tag": result.record.snapshot_tag,
            "language": result.record.language,
            "character_id": result.record.character_id,
            "act_id": result.record.act_id,
            "seed": result.record.seed,
            "floors_requested": scenario["floors"],
            "floors_cleared": result.record.floor,
            "victory": result.record.victory,
            "hp": result.record.player.hp,
            "max_hp": result.record.player.max_hp,
            "gold": result.record.player.gold,
            "deck_size": len(result.record.player.deck_definition_ids),
            "relic_count": len(result.record.player.relic_ids),
            "potion_count": len(result.record.player.potion_ids),
            "issue_count": sum(
                1
                for line in result.record.transcript
                if any(marker in line for marker in UNRESOLVED_MARKERS)
            ),
        }

        assert transcript == expected_transcript, scenario["slug"]
        assert actual_summary == expected_summary, scenario["slug"]
        assert actual_summary["issue_count"] == 0, scenario["slug"]