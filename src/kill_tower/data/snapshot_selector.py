from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kill_tower.app.config import AppConfig, get_config
from kill_tower.data.loader import load_manifest
from kill_tower.data.schemas import SnapshotManifest


@dataclass(slots=True)
class SnapshotRecord:
    tag: str
    manifest_path: Path
    manifest: SnapshotManifest
    raw_dir: Path
    normalized_dir: Path
    available_languages: tuple[str, ...]

    def has_language(self, lang: str) -> bool:
        return lang in self.available_languages


class SnapshotSelector:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or get_config()

    def list_snapshots(self) -> list[SnapshotRecord]:
        records: list[SnapshotRecord] = []
        for snapshot_dir in sorted(self.config.paths.snapshots_dir.iterdir()):
            if not snapshot_dir.is_dir():
                continue
            manifest_path = snapshot_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = load_manifest(snapshot_dir.name)
            normalized_dir = self.config.paths.normalized_data_dir / snapshot_dir.name
            languages = tuple(
                sorted(path.name for path in normalized_dir.iterdir() if path.is_dir())
            ) if normalized_dir.exists() else ()
            records.append(
                SnapshotRecord(
                    tag=snapshot_dir.name,
                    manifest_path=manifest_path,
                    manifest=manifest,
                    raw_dir=self.config.paths.raw_data_dir / "spire_codex" / snapshot_dir.name,
                    normalized_dir=normalized_dir,
                    available_languages=languages,
                )
            )
        return sorted(records, key=lambda item: (item.manifest.fetched_at, item.tag), reverse=True)

    def resolve(self, snapshot_tag: str | None = None) -> SnapshotRecord:
        explicit_tag = snapshot_tag or self.config.runtime.default_snapshot_tag
        snapshots = self.list_snapshots()
        if explicit_tag is not None:
            for record in snapshots:
                if record.tag == explicit_tag:
                    return record
            raise FileNotFoundError(f"Snapshot not found: {explicit_tag}")
        if not snapshots:
            raise FileNotFoundError("No snapshots available.")
        return snapshots[0]