from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kill_tower.app.config import get_config
from kill_tower.data.loader import write_json
from kill_tower.data.schemas import ManifestCounts, SnapshotManifest

DEFAULT_ENDPOINTS = (
    "characters",
    "cards",
    "relics",
    "potions",
    "monsters",
    "encounters",
    "events",
    "powers",
    "keywords",
    "intents",
    "orbs",
    "afflictions",
    "modifiers",
    "acts",
    "ascensions",
    "achievements",
)


def fetch_collection(client: httpx.Client, base_url: str, endpoint: str, lang: str) -> Any:
    response = client.get(
        f"{base_url.rstrip('/')}/api/{endpoint}",
        params={"lang": lang},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def build_counts(downloads: dict[str, Any]) -> ManifestCounts:
    counts_payload: dict[str, int] = {}
    for key in ManifestCounts.model_fields:
        payload = downloads.get(key)
        if isinstance(payload, list):
            counts_payload[key] = len(payload)
    return ManifestCounts(**counts_payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch raw JSON exports from Spire Codex.")
    parser.add_argument("snapshot_tag", help="Snapshot tag, for example 2026-03-09_build_12345")
    parser.add_argument("--lang", action="append", default=["eng", "zhs"], dest="languages")
    parser.add_argument("--endpoint", action="append", dest="endpoints")
    parser.add_argument("--base-url", default=get_config().runtime.spire_codex_api_base)
    parser.add_argument("--game-version", default="TBD")
    parser.add_argument("--build-id", default="TBD")
    parser.add_argument("--skip-manifest", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config()
    endpoints = tuple(dict.fromkeys(args.endpoints or DEFAULT_ENDPOINTS))
    languages = tuple(dict.fromkeys(args.languages))
    first_lang_downloads: dict[str, Any] = {}

    with httpx.Client() as client:
        for lang in languages:
            for endpoint in endpoints:
                payload = fetch_collection(client, args.base_url, endpoint, lang)
                if lang == languages[0]:
                    first_lang_downloads[endpoint] = payload
                output_path = (
                    config.paths.raw_data_dir
                    / "spire_codex"
                    / args.snapshot_tag
                    / lang
                    / f"{endpoint}.json"
                )
                write_json(output_path, payload)
                print(f"saved {output_path}")

    if args.skip_manifest:
        return

    manifest = SnapshotManifest(
        snapshot_tag=args.snapshot_tag,
        game_version=args.game_version,
        build_id=args.build_id,
        fetched_at=datetime.now(timezone.utc),
        sources=[args.base_url],
        counts=build_counts(first_lang_downloads),
    )
    manifest_path = config.paths.snapshots_dir / args.snapshot_tag / "manifest.json"
    write_json(manifest_path, manifest.model_dump(mode="json"))
    print(f"saved {manifest_path}")


if __name__ == "__main__":
    main()