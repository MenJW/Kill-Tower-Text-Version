from __future__ import annotations


class TranscriptService:
    def __init__(self) -> None:
        self._lines: list[str] = []

    def record(self, message: str) -> None:
        self._lines.append(message)

    def extend(self, messages: list[str]) -> None:
        self._lines.extend(messages)

    def lines(self) -> list[str]:
        return list(self._lines)

    def export(self) -> str:
        return "\n".join(self._lines)