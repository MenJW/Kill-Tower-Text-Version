from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from kill_tower.app.config import get_config
from kill_tower.ui.keymaps import DEFAULT_BINDINGS


class KillTowerApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        layout: vertical;
        padding: 1 2;
    }

    #panels {
        layout: horizontal;
        height: 1fr;
    }

    .panel {
        border: round $accent;
        padding: 1;
        width: 1fr;
        margin-bottom: 1;
    }

    #hero {
        height: 5;
    }

    #log {
        height: 10;
    }
    """
    TITLE = "Kill Tower"
    SUB_TITLE = "Text Version Scaffold"
    BINDINGS = [Binding(item.key, item.action, item.description) for item in DEFAULT_BINDINGS]

    def compose(self) -> ComposeResult:
        config = get_config()
        yield Header()
        with Vertical(id="body"):
            yield Static(self._hero_text(), id="hero", classes="panel")
            with Horizontal(id="panels"):
                yield Static(self._project_panel(config), id="project", classes="panel")
                yield Static(self._next_steps_panel(), id="next-steps", classes="panel")
            yield Static(self._log_text(), id="log", classes="panel")
        yield Footer()

    def action_show_paths(self) -> None:
        config = get_config()
        lines = [
            "Paths",
            f"root: {config.paths.root}",
            f"raw: {config.paths.raw_data_dir}",
            f"normalized: {config.paths.normalized_data_dir}",
            f"snapshots: {config.paths.snapshots_dir}",
            f"saves: {config.paths.saves_dir}",
        ]
        self.query_one("#log", Static).update("\n".join(lines))

    def action_show_status(self) -> None:
        self.query_one("#log", Static).update(self._status_text())

    def _hero_text(self) -> str:
        return "Kill Tower Text Version\nProject scaffold initialized."

    def _project_panel(self, config) -> str:
        return "\n".join(
            [
                "Project",
                f"name: {config.runtime.project_name}",
                f"lang: {config.runtime.default_language}",
                f"fallback: {config.runtime.fallback_language}",
                f"snapshot: {config.runtime.default_snapshot_tag}",
            ]
        )

    def _next_steps_panel(self) -> str:
        return "\n".join(
            [
                "Next steps",
                "1. Import a snapshot manifest",
                "2. Normalize raw entity files",
                "3. Fill out combat scripts",
                "4. Replace placeholder UI screens",
            ]
        )

    def _status_text(self) -> str:
        return "\n".join(
            [
                "Status",
                "- Package layout ready",
                "- CLI ready",
                "- Data schemas ready",
                "- Engine shell ready",
                "- TUI shell ready",
            ]
        )

    def _log_text(self) -> str:
        return "\n".join(
            [
                "Log",
                "- Press s to view scaffold status.",
                "- Press p to inspect configured paths.",
                "- Replace this shell with combat and run screens next.",
            ]
        )