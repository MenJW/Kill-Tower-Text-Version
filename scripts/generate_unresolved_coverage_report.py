from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kill_tower.app.config import get_config
from kill_tower.services.coverage_service import CoverageService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate unresolved entity coverage report.")
    parser.add_argument("snapshot_tag", help="Snapshot tag to analyze")
    parser.add_argument("--langs", nargs="+", default=["eng", "zhs"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config()
    report_dir = config.paths.reports_dir / args.snapshot_tag
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = report_dir / "unresolved-coverage.md"
    json_path = report_dir / "unresolved-coverage.json"

    service = CoverageService()
    reports = [service.generate_language_report(args.snapshot_tag, lang) for lang in args.langs]

    markdown_path.write_text(service.render_markdown(reports), encoding="utf-8")
    json_path.write_text(
        json.dumps({"reports": [report.to_dict() for report in reports]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"saved {markdown_path}")
    print(f"saved {json_path}")


if __name__ == "__main__":
    main()
