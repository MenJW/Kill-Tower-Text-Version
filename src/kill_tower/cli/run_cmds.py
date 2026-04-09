from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from kill_tower.data.service import DataService
from kill_tower.engine.action_queue import Action, ActionQueue
from kill_tower.engine.combat import CombatRuntime
from kill_tower.engine.rng import SeededRNG
from kill_tower.services.transcript_service import TranscriptService
from kill_tower.ui.app import KillTowerApp

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Runtime commands.")
console = Console()


@app.command("ui")
def ui() -> None:
    KillTowerApp().run()


@app.command("smoke")
def smoke(seed: int = typer.Option(0, help="Deterministic smoke-run seed.")) -> None:
    rng = SeededRNG(seed)
    queue = ActionQueue()
    transcript = TranscriptService()
    queue.push(Action(name="boot", source_id="system", payload={"seed": seed}))
    transcript.record(f"Smoke run initialized with seed {seed}.")
    transcript.record(f"Preview random value: {rng.randint(1, 99)}")
    console.print(transcript.export())
    console.print(f"Queued actions: {len(queue)}")


@app.command("vertical-slice")
def vertical_slice(
    snapshot_tag: str | None = typer.Option(None, help="Snapshot tag to load."),
    lang: str = typer.Option("eng", help="Normalized language to load."),
    character_id: str = typer.Option("ironclad", help="Character id."),
    encounter_id: str = typer.Option("toadpoles-normal", help="Encounter id."),
    seed: int = typer.Option(7, help="Deterministic combat seed."),
    max_turns: int = typer.Option(12, help="Turn limit for the demo battle."),
) -> None:
    data_service = DataService()
    bundle = data_service.load_bundle(snapshot_tag=snapshot_tag, lang=lang)
    runtime = CombatRuntime(bundle.registry, seed=seed, snapshot_tag=bundle.snapshot.tag)
    result = runtime.run_vertical_slice(
        character_id=character_id,
        encounter_id=encounter_id,
        max_turns=max_turns,
    )

    table = Table(title="Vertical Slice Result")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("snapshot", str(result.snapshot_tag))
    table.add_row("character", result.character_id)
    table.add_row("encounter", result.encounter_id)
    table.add_row("victory", str(result.victory))
    table.add_row("turns", str(result.turns))
    table.add_row("hp", f"{result.player_hp}/{result.max_player_hp}")
    console.print(table)
    console.print("\n".join(result.transcript))