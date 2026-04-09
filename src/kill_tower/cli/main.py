from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from kill_tower.app.config import get_config
from kill_tower.cli.data_cmds import app as data_app
from kill_tower.cli.debug_cmds import app as debug_app
from kill_tower.cli.run_cmds import app as run_app

console = Console()
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Kill Tower project CLI.",
)
app.add_typer(data_app, name="data")
app.add_typer(run_app, name="run")
app.add_typer(debug_app, name="debug")


@app.command()
def info() -> None:
    config = get_config()
    table = Table(title="Kill Tower Project Info")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Project", config.runtime.project_name)
    table.add_row("Root", str(config.paths.root))
    table.add_row("Default language", config.runtime.default_language)
    table.add_row("Fallback language", config.runtime.fallback_language)
    table.add_row("Default snapshot", str(config.runtime.default_snapshot_tag))
    console.print(table)


def run() -> None:
    app()


if __name__ == "__main__":
    run()