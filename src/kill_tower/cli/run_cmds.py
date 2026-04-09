from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from kill_tower.data.service import DataService
from kill_tower.engine.action_queue import Action, ActionQueue
from kill_tower.engine.combat import CombatRuntime
from kill_tower.engine.rng import SeededRNG
from kill_tower.services.run_service import RunService
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


@app.command("auto")
def auto_run(
    snapshot_tag: str | None = typer.Option(None, help="Snapshot tag to load."),
    lang: str = typer.Option("eng", help="Normalized language to load."),
    character_id: str = typer.Option("ironclad", help="Character id."),
    act_id: str | None = typer.Option(None, help="Act id to route through."),
    seed: int = typer.Option(7, help="Deterministic run seed."),
    floors: int = typer.Option(5, min=1, help="How many floors to resolve automatically."),
    ascension_level: int = typer.Option(0, min=0, help="Ascension level to apply."),
    slot: str | None = typer.Option(None, help="Optional save slot name."),
) -> None:
    run_service = RunService()
    result = run_service.run_auto(
        character_id=character_id,
        snapshot_tag=snapshot_tag,
        lang=lang,
        act_id=act_id,
        seed=seed,
        floors=floors,
        ascension_level=ascension_level,
    )
    save_path = None
    if slot is not None:
        save_path = run_service.save_run(slot, result.record, result.replay)

    table = Table(title="Auto Run Result")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("snapshot", result.record.snapshot_tag)
    table.add_row("act", result.record.act_id)
    table.add_row("ascension", str(result.record.ascension_level))
    table.add_row("character", result.record.character_id)
    table.add_row("floors cleared", str(result.record.floor))
    table.add_row("victory", str(result.record.victory))
    table.add_row("hp", f"{result.record.player.hp}/{result.record.player.max_hp}")
    table.add_row("gold", str(result.record.player.gold))
    table.add_row("deck size", str(len(result.record.player.deck_definition_ids)))
    table.add_row(
        "potions",
        f"{len(result.record.player.potion_ids)}/{result.record.player.max_potion_slots}",
    )
    if save_path is not None:
        table.add_row("save", str(save_path))
    console.print(table)
    console.print("\n".join(result.record.transcript))