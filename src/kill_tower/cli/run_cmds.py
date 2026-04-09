from __future__ import annotations

import typer
from rich.console import Console

from kill_tower.engine.action_queue import Action, ActionQueue
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