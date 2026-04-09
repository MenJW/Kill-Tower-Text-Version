from __future__ import annotations

from dataclasses import dataclass

from kill_tower.app.config import AppConfig, get_config
from kill_tower.data.loader import load_manifest
from kill_tower.data.registry import ContentRegistry, build_registry
from kill_tower.data.schemas import SnapshotManifest
from kill_tower.data.snapshot_selector import SnapshotRecord, SnapshotSelector


@dataclass(slots=True)
class SnapshotBundle:
    snapshot: SnapshotRecord
    language: str
    registry: ContentRegistry


class DataService:
    def __init__(
        self,
        config: AppConfig | None = None,
        selector: SnapshotSelector | None = None,
    ) -> None:
        self.config = config or get_config()
        self.selector = selector or SnapshotSelector(self.config)
        self._registry_cache: dict[tuple[str, str], ContentRegistry] = {}

    def list_snapshots(self) -> list[SnapshotRecord]:
        return self.selector.list_snapshots()

    def select_snapshot(self, snapshot_tag: str | None = None) -> SnapshotRecord:
        return self.selector.resolve(snapshot_tag)

    def load_manifest(self, snapshot_tag: str | None = None) -> SnapshotManifest:
        snapshot = self.select_snapshot(snapshot_tag)
        return load_manifest(snapshot.tag)

    def load_registry(self, snapshot_tag: str | None = None, lang: str | None = None) -> ContentRegistry:
        bundle = self.load_bundle(snapshot_tag=snapshot_tag, lang=lang)
        return bundle.registry

    def load_bundle(self, snapshot_tag: str | None = None, lang: str | None = None) -> SnapshotBundle:
        snapshot = self.select_snapshot(snapshot_tag)
        resolved_lang = self._resolve_language(snapshot, lang)
        key = (snapshot.tag, resolved_lang)
        if key not in self._registry_cache:
            self._registry_cache[key] = build_registry(snapshot.normalized_dir / resolved_lang)
        return SnapshotBundle(snapshot=snapshot, language=resolved_lang, registry=self._registry_cache[key])

    def _resolve_language(self, snapshot: SnapshotRecord, requested_lang: str | None) -> str:
        candidates = [
            requested_lang,
            self.config.runtime.default_language,
            self.config.runtime.fallback_language,
        ]
        for candidate in candidates:
            if candidate and snapshot.has_language(candidate):
                return candidate
        if snapshot.available_languages:
            return snapshot.available_languages[0]
        raise FileNotFoundError(f"Snapshot {snapshot.tag} has no normalized languages.")