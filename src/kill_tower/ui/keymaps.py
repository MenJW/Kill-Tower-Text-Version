from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyBindingSpec:
    key: str
    action: str
    description: str


DEFAULT_BINDINGS: tuple[KeyBindingSpec, ...] = (
    KeyBindingSpec("q", "quit", "Quit"),
    KeyBindingSpec("p", "show_paths", "Paths"),
    KeyBindingSpec("s", "show_status", "Status"),
)