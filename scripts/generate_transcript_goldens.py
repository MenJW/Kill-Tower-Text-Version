from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kill_tower.services.run_service import RunService


SCENARIOS: list[dict[str, Any]] = [
    {"lang": "eng", "character_id": "ironclad", "act_id": "underdocks", "seed": 7, "floors": 7},
    {"lang": "eng", "character_id": "silent", "act_id": "underdocks", "seed": 7, "floors": 7},
    {"lang": "eng", "character_id": "defect", "act_id": "underdocks", "seed": 7, "floors": 7},
    {"lang": "zhs", "character_id": "ironclad", "act_id": "underdocks", "seed": 7, "floors": 7},
    {"lang": "zhs", "character_id": "silent", "act_id": "underdocks", "seed": 7, "floors": 7},
    {"lang": "zhs", "character_id": "defect", "act_id": "underdocks", "seed": 7, "floors": 7},
]

UNRESOLVED_MARKERS = (
    "still has unimplemented clauses",
    "used number-only fallback resolution",
    "has no executable script yet",
    "Unsupported event effect",
)


def scenario_slug(scenario: dict[str, Any]) -> str:
    return (
        f"{scenario['character_id']}-{scenario['act_id']}-seed{scenario['seed']}-floors{scenario['floors']}"
    )


def build_summary(result: Any, scenario: dict[str, Any]) -> dict[str, Any]:
    transcript = result.record.transcript
    issue_count = sum(1 for line in transcript if any(marker in line for marker in UNRESOLVED_MARKERS))
    return {
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
        "issue_count": issue_count,
    }


def main() -> None:
    golden_dir = ROOT / "tests" / "golden" / "transcripts"
    manifest_path = golden_dir / "manifest.json"
    service = RunService()

    manifest: dict[str, Any] = {"scenarios": []}
    for scenario in SCENARIOS:
        result = service.run_auto(
            character_id=scenario["character_id"],
            snapshot_tag="2026-04-09_build_unknown",
            lang=scenario["lang"],
            act_id=scenario["act_id"],
            seed=scenario["seed"],
            floors=scenario["floors"],
        )
        slug = scenario_slug(scenario)
        lang_dir = golden_dir / scenario["lang"]
        lang_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = lang_dir / f"{slug}.txt"
        summary_path = lang_dir / f"{slug}.summary.json"
        transcript_path.write_text("\n".join(result.record.transcript) + "\n", encoding="utf-8")
        summary = build_summary(result, scenario)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["scenarios"].append(
            {
                **scenario,
                "slug": slug,
                "summary": summary,
            }
        )
        print(f"saved {transcript_path}")
        print(f"saved {summary_path}")

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {manifest_path}")


if __name__ == "__main__":
    main()
