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
from kill_tower.data.loader import load_json, load_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a simple gap report from normalized JSON.")
    parser.add_argument("snapshot_tag", help="Snapshot tag to summarize")
    parser.add_argument("--lang", default="eng")
    return parser.parse_args()


def summarize_collection(payload: Any) -> tuple[int, int]:
    if not isinstance(payload, list):
        return 0, 0
    total = len(payload)
    implemented = sum(1 for item in payload if isinstance(item, dict) and item.get("implemented"))
    return total, implemented


def main() -> None:
    args = parse_args()
    config = get_config()
    normalized_dir = config.paths.normalized_data_dir / args.snapshot_tag / args.lang
    report_dir = config.paths.reports_dir / args.snapshot_tag
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "gap-report.md"

    manifest = load_manifest(args.snapshot_tag)
    lines = [
        f"# Gap Report: {args.snapshot_tag}",
        "",
        f"- Game version: {manifest.game_version}",
        f"- Build id: {manifest.build_id}",
        f"- Language: {args.lang}",
        "",
        "| Entity | Total | Implemented |",
        "| --- | ---: | ---: |",
    ]

    for file_path in sorted(normalized_dir.glob("*.json")):
        total, implemented = summarize_collection(load_json(file_path))
        lines.append(f"| {file_path.stem} | {total} | {implemented} |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {report_path}")


if __name__ == "__main__":
    main()