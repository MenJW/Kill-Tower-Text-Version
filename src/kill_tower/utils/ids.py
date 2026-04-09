from __future__ import annotations

import re


def slugify_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return slug.strip("-")


def make_snapshot_tag(date_part: str, build_id: str) -> str:
    return f"{date_part}_build_{build_id}"