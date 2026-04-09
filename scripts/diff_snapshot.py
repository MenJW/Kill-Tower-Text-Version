from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kill_tower.app.config import get_config
from kill_tower.data.loader import load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diff normalized snapshot entity ids.")
    parser.add_argument("left_snapshot")
    parser.add_argument("right_snapshot")
    parser.add_argument("--lang", default="eng")
    return parser.parse_args()


def extract_ids(payload: Any) -> set[str]:
    if not isinstance(payload, list):
        return set()
    return {
        str(item.get("id"))
        for item in payload
        if isinstance(item, dict) and item.get("id") is not None
    }


def main() -> None:
    args = parse_args()
    config = get_config()
    left_dir = config.paths.normalized_data_dir / args.left_snapshot / args.lang
    right_dir = config.paths.normalized_data_dir / args.right_snapshot / args.lang

    for left_file in sorted(left_dir.glob("*.json")):
        right_file = right_dir / left_file.name
        if not right_file.exists():
            print(f"missing on right: {right_file}")
            continue
        left_ids = extract_ids(load_json(left_file))
        right_ids = extract_ids(load_json(right_file))
        added = sorted(right_ids - left_ids)
        removed = sorted(left_ids - right_ids)
        if added or removed:
            print(f"[{left_file.stem}]")
            if added:
                print(f"  added: {', '.join(added[:10])}")
            if removed:
                print(f"  removed: {', '.join(removed[:10])}")


if __name__ == "__main__":
    main()