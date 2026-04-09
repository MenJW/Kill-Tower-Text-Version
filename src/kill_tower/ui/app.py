from __future__ import annotations

from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from kill_tower.app.config import get_config
from kill_tower.services.run_service import AutoRunResult, RunService
from kill_tower.ui.keymaps import DEFAULT_BINDINGS


@dataclass(slots=True)
class ScenarioSelection:
    lang: str = "zhs"
    character_id: str = "ironclad"
    seed: int = 7
    full_act: bool = False
    ascension_level: int = 0

    @property
    def floors(self) -> int | None:
        return None if self.full_act else 7


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
    SUB_TITLE = "Auto-Run Preview"
    BINDINGS = [Binding(item.key, item.action, item.description) for item in DEFAULT_BINDINGS]

    def __init__(self) -> None:
        super().__init__()
        config = get_config()
        self.selection = ScenarioSelection(lang=config.runtime.default_language)
        self.run_service = RunService()
        self._characters = ["ironclad", "silent", "defect", "regent", "necrobinder"]
        self._languages = ["zhs", "eng"]
        self._last_result: AutoRunResult | None = None
        self._last_error: str | None = None

    def compose(self) -> ComposeResult:
        config = get_config()
        yield Header()
        with Vertical(id="body"):
            yield Static(self._hero_text(), id="hero", classes="panel")
            with Horizontal(id="panels"):
                yield Static(self._scenario_panel(config), id="project", classes="panel")
                yield Static(self._controls_panel(), id="next-steps", classes="panel")
            yield Static(self._log_text(), id="log", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self.action_run_current)

    def action_run_current(self) -> None:
        config = get_config()
        try:
            result = self.run_service.run_auto(
                character_id=self.selection.character_id,
                snapshot_tag=config.runtime.default_snapshot_tag or "2026-04-09_build_unknown",
                lang=self.selection.lang,
                act_id="underdocks",
                seed=self.selection.seed,
                floors=self.selection.floors,
                ascension_level=self.selection.ascension_level,
            )
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self._last_result = None
        else:
            self._last_result = result
            self._last_error = None
        self._refresh_screen()

    def action_next_character(self) -> None:
        current_index = self._characters.index(self.selection.character_id)
        self.selection.character_id = self._characters[(current_index + 1) % len(self._characters)]
        self._refresh_screen()

    def action_toggle_language(self) -> None:
        current_index = self._languages.index(self.selection.lang)
        self.selection.lang = self._languages[(current_index + 1) % len(self._languages)]
        self._refresh_screen()

    def action_toggle_full_act(self) -> None:
        self.selection.full_act = not self.selection.full_act
        self._refresh_screen()

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
        if self._last_error is not None:
            return f"Kill Tower 中文单人版\n预览运行失败: {self._last_error}"
        if self._last_result is None:
            return "Kill Tower 中文单人版\n按 r 运行自动预览，终端使用 kill-tower run play 进入手动模式。"
        record = self._last_result.record
        return (
            "Kill Tower 中文自动预览\n"
            f"{record.player.name} | {'完整一局预览' if self.selection.full_act else '7层预览'} | "
            f"胜利: {record.victory} | 楼层: {record.floor} | HP: {record.player.hp}/{record.player.max_hp}"
        )

    def _project_panel(self, config) -> str:
        return self._scenario_panel(config)

    def _scenario_panel(self, config) -> str:
        return "\n".join(
            [
                "当前局面",
                f"项目: {config.runtime.project_name}",
                f"语言: {self.selection.lang}",
                f"角色: {self.selection.character_id}",
                f"模式: {'完整一局自动预览' if self.selection.full_act else '7层稳定预览'}",
                f"seed: {self.selection.seed}",
                f"snapshot: {config.runtime.default_snapshot_tag or '2026-04-09_build_unknown'}",
            ]
        )

    def _controls_panel(self) -> str:
        return "\n".join(
            [
                "操作",
                "r: 以当前配置重新跑自动预览",
                "c: 切换角色",
                "l: 切换语言 zhs/eng",
                "f: 切换 7层 / 完整一局",
                "s: 查看运行状态",
                "p: 查看路径",
                "终端手动游玩: kill-tower run play",
            ]
        )

    def _status_text(self) -> str:
        if self._last_result is None:
            return "状态\n- 还没有完成任何一次跑局。\n- 按 r 开始当前配置。"
        unresolved = sum(
            1
            for line in self._last_result.record.transcript
            if "Unsupported event effect" in line
            or "unimplemented clauses" in line
            or "has no executable script yet" in line
            or "number-only fallback" in line
        )
        return "\n".join(
            [
                "状态",
                f"- 语言: {self._last_result.record.language}",
                f"- 角色: {self._last_result.record.character_id}",
                f"- 胜利: {self._last_result.record.victory}",
                f"- 楼层: {self._last_result.record.floor}",
                f"- 未解析标记: {unresolved}",
                f"- 金币: {self._last_result.record.player.gold}",
            ]
        )

    def _log_text(self) -> str:
        if self._last_error is not None:
            return f"日志\n- {self._last_error}"
        if self._last_result is None:
            return "日志\n- 等待开始新一局。"
        transcript = self._last_result.record.transcript[-36:]
        return "日志\n" + "\n".join(transcript)

    def _refresh_screen(self) -> None:
        config = get_config()
        self.query_one("#hero", Static).update(self._hero_text())
        self.query_one("#project", Static).update(self._scenario_panel(config))
        self.query_one("#next-steps", Static).update(self._controls_panel())
        self.query_one("#log", Static).update(self._log_text())