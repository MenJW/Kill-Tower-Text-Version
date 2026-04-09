from __future__ import annotations

from pathlib import Path
from typing import Any

from kill_tower.app.config import get_config
from kill_tower.data.loader import load_json, write_json


class SaveService:
    def __init__(self, base_dir: Path | None = None) -> None:
        config = get_config()
        self.base_dir = base_dir or config.paths.saves_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, slot: str, payload: dict[str, Any]) -> Path:
        save_path = self.base_dir / f"{slot}.json"
        write_json(save_path, payload)
        return save_path

    def load_run(self, slot: str) -> dict[str, Any]:
        return load_json(self.base_dir / f"{slot}.json")

    def list_slots(self) -> list[str]:
        return sorted(path.stem for path in self.base_dir.glob("*.json"))