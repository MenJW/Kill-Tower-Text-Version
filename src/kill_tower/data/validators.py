from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kill_tower.data.loader import load_manifest
from kill_tower.data.registry import ContentRegistry


@dataclass(slots=True)
class ValidationIssue:
    level: str
    message: str


def validate_registry(registry: ContentRegistry, required_languages: set[str] | None = None) -> list[ValidationIssue]:
    required_languages = required_languages or {"eng", "zhs"}
    issues: list[ValidationIssue] = []

    for collection_name, collection in registry.summary().items():
        if collection == 0:
            issues.append(ValidationIssue("warning", f"Collection {collection_name} is empty."))

    for entity_group in [
        registry.characters,
        registry.cards,
        registry.relics,
        registry.potions,
        registry.enchantments,
        registry.monsters,
        registry.events,
        registry.encounters,
        registry.powers,
        registry.keywords,
        registry.intents,
        registry.orbs,
        registry.afflictions,
        registry.modifiers,
        registry.acts,
        registry.ascensions,
        registry.achievements,
    ]:
        for entity in entity_group.values():
            missing_languages = required_languages - set(entity.texts)
            if missing_languages:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"{entity.id} is missing languages: {', '.join(sorted(missing_languages))}",
                    )
                )
    return issues


def validate_manifest_directory(snapshot_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.exists():
        return [ValidationIssue("error", f"Missing manifest: {manifest_path}")]

    manifest = load_manifest(snapshot_dir.name)
    if manifest.snapshot_tag != snapshot_dir.name:
        issues.append(
            ValidationIssue(
                "error",
                f"Snapshot tag mismatch: manifest={manifest.snapshot_tag} dir={snapshot_dir.name}",
            )
        )
    return issues