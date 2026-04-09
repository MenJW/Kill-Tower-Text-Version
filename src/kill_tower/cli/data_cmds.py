from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kill_tower.app.config import get_config
from kill_tower.data.service import DataService
from kill_tower.data.loader import write_json
from kill_tower.data.schemas import ManifestCounts, SnapshotManifest

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Data and snapshot commands.")
console = Console()


@app.command("paths")
def paths() -> None:
    config = get_config()
    for name, value in config.paths.model_dump().items():
        console.print(f"{name}: {value}")


@app.command("snapshots")
def snapshots() -> None:
    service = DataService()
    table = Table(title="Available Snapshots")
    table.add_column("tag")
    table.add_column("version")
    table.add_column("languages")
    for snapshot in service.list_snapshots():
        table.add_row(
            snapshot.tag,
            snapshot.manifest.game_version,
            ", ".join(snapshot.available_languages),
        )
    console.print(table)


@app.command("registry-summary")
def registry_summary(
    snapshot_tag: str | None = typer.Option(None, help="Snapshot tag to inspect."),
    lang: str = typer.Option("eng", help="Language to load."),
) -> None:
    service = DataService()
    registry = service.load_registry(snapshot_tag=snapshot_tag, lang=lang)
    table = Table(title="Registry Summary")
    table.add_column("entity")
    table.add_column("count")
    for entity, count in registry.summary().items():
        table.add_row(entity, str(count))
    console.print(table)


@app.command("init-manifest")
def init_manifest(
    snapshot_tag: str = typer.Argument(..., help="Snapshot tag, for example 2026-03-09_build_12345."),
    game_version: str = typer.Option("TBD", help="Game version string."),
    build_id: str = typer.Option("TBD", help="Steam build id."),
    output: Path | None = typer.Option(None, help="Explicit manifest output path."),
) -> None:
    config = get_config()
    manifest_path = output or config.paths.snapshots_dir / snapshot_tag / "manifest.json"
    manifest = SnapshotManifest(
        game_version=game_version,
        build_id=build_id,
        snapshot_tag=snapshot_tag,
        fetched_at=datetime.now(timezone.utc),
        sources=[
            config.runtime.spire_codex_api_base,
            config.runtime.kotone_reference_url,
        ],
        counts=ManifestCounts(),
    )
    write_json(manifest_path, manifest.model_dump(mode="json"))
    console.print(f"Manifest written to {manifest_path}")