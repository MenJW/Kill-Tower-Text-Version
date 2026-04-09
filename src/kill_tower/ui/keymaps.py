from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyBindingSpec:
    key: str
    action: str
    description: str


DEFAULT_BINDINGS: tuple[KeyBindingSpec, ...] = (
    KeyBindingSpec("q", "quit", "Quit"),
    KeyBindingSpec("r", "run_current", "Run"),
    KeyBindingSpec("c", "next_character", "Character"),
    KeyBindingSpec("l", "toggle_language", "Language"),
    KeyBindingSpec("f", "toggle_full_act", "Full Act"),
    KeyBindingSpec("p", "show_paths", "Paths"),
    KeyBindingSpec("s", "show_status", "Status"),
)