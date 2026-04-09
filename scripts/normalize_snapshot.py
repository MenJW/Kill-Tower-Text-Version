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
from kill_tower.data.normalizers import build_language_index, normalize_entity, sort_normalized_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize raw snapshot data into project shape.")
    parser.add_argument("snapshot_tag", help="Snapshot tag to normalize")
    parser.add_argument("--lang", action="append", default=["eng", "zhs"], dest="languages")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config()
    raw_root = config.paths.raw_data_dir / "spire_codex" / args.snapshot_tag
    endpoints = sorted(
        {
            path.stem
            for lang in tuple(dict.fromkeys(args.languages))
            for path in (raw_root / lang).glob("*.json")
        }
    )

    for endpoint in endpoints:
        payloads_by_lang: dict[str, Any] = {}
        for lang in tuple(dict.fromkeys(args.languages)):
            raw_file = raw_root / lang / f"{endpoint}.json"
            if raw_file.exists():
                payloads_by_lang[lang] = load_json(raw_file)

        if not payloads_by_lang:
            continue

        entity_index = build_language_index(payloads_by_lang)
        for lang in tuple(dict.fromkeys(args.languages)):
            output_dir = config.paths.normalized_data_dir / args.snapshot_tag / lang
            output_dir.mkdir(parents=True, exist_ok=True)
            normalized_records = [
                normalize_entity(
                    endpoint=endpoint,
                    records_by_lang=records,
                    preferred_lang=lang,
                    snapshot_tag=args.snapshot_tag,
                    base_url=config.runtime.spire_codex_api_base,
                )
                for records in entity_index.values()
            ]
            output_path = output_dir / f"{endpoint}.json"
            write_json(output_path, sort_normalized_records(normalized_records))
            print(f"saved {output_path}")


if __name__ == "__main__":
    main()