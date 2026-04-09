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
from kill_tower.data.loader import load_json, write_json
from kill_tower.utils.text import collapse_whitespace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize raw snapshot data into project shape.")
    parser.add_argument("snapshot_tag", help="Snapshot tag to normalize")
    parser.add_argument("--lang", action="append", default=["eng", "zhs"], dest="languages")
    return parser.parse_args()


def normalize_record(record: dict[str, Any], lang: str) -> dict[str, Any]:
    source_id = str(record.get("id") or record.get("source_id") or record.get("name") or "unknown")
    name = collapse_whitespace(str(record.get("name") or source_id))
    description = record.get("description")

    normalized = dict(record)
    normalized["id"] = source_id
    normalized["source_id"] = source_id
    normalized.setdefault(
        "texts",
        {
            lang: {
                "name": name,
                "description": collapse_whitespace(str(description)) if description else None,
            }
        },
    )
    normalized.setdefault("scripted", False)
    normalized.setdefault("implemented", False)
    return normalized


def normalize_collection(records: Any, lang: str) -> Any:
    if isinstance(records, list):
        return [normalize_record(record, lang) for record in records if isinstance(record, dict)]
    return records


def main() -> None:
    args = parse_args()
    config = get_config()

    for lang in tuple(dict.fromkeys(args.languages)):
        raw_dir = config.paths.raw_data_dir / "spire_codex" / args.snapshot_tag / lang
        output_dir = config.paths.normalized_data_dir / args.snapshot_tag / lang
        output_dir.mkdir(parents=True, exist_ok=True)
        for raw_file in sorted(raw_dir.glob("*.json")):
            payload = load_json(raw_file)
            normalized = normalize_collection(payload, lang)
            output_path = output_dir / raw_file.name
            write_json(output_path, normalized)
            print(f"saved {output_path}")


if __name__ == "__main__":
    main()