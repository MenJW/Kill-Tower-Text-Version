from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kill_tower.app.config import get_config

DEFAULT_PAGES = ("", "cards", "relics", "system")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch raw HTML reference pages from Kotone Workshop.")
    parser.add_argument("snapshot_tag", help="Snapshot tag, for example 2026-03-09_build_12345")
    parser.add_argument("--page", action="append", dest="pages")
    parser.add_argument("--base-url", default=get_config().runtime.kotone_reference_url)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config()
    pages = tuple(dict.fromkeys(args.pages or DEFAULT_PAGES))
    output_dir = config.paths.raw_data_dir / "kotone_reference" / args.snapshot_tag
    output_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        for page in pages:
            page_path = page.strip("/")
            suffix = page_path or "index"
            url = args.base_url.rstrip("/")
            if page_path:
                url = f"{url}/{page_path}"
            response = client.get(url, timeout=60)
            response.raise_for_status()
            file_path = output_dir / f"{suffix}.html"
            file_path.write_text(response.text, encoding="utf-8")
            print(f"saved {file_path}")


if __name__ == "__main__":
    main()