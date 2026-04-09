from __future__ import annotations

import typer
from rich.console import Console

from kill_tower.app.config import get_config
from kill_tower.engine.rng import SeededRNG

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Debug helpers.")
console = Console()


@app.command("config")
def config() -> None:
    console.print(get_config().model_dump_json(indent=2))


@app.command("seed")
def seed_preview(seed: int = typer.Argument(..., help="Seed to preview.")) -> None:
    rng = SeededRNG(seed)
    preview = [rng.randint(0, 9999) for _ in range(5)]
    console.print({"seed": seed, "preview": preview})