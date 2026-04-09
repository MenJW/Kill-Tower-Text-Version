from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kill_tower.data.loader import load_manifest


@dataclass(slots=True)
class ParitySummary:
    snapshot_tag: str
    expected_counts: dict[str, int]
    observed_files: dict[str, int]


class ParityService:
    def summarize_snapshot(self, snapshot_dir: Path) -> ParitySummary:
        manifest = load_manifest(snapshot_dir.name)
        observed = {
            path.stem: 1
            for path in sorted(snapshot_dir.rglob("*.json"))
            if path.name != "manifest.json"
        }
        return ParitySummary(
            snapshot_tag=manifest.snapshot_tag,
            expected_counts=manifest.counts.model_dump(),
            observed_files=observed,
        )