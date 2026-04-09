from __future__ import annotations

import re


CAMEL_BOUNDARY_1 = re.compile(r"([a-z0-9])([A-Z])")
CAMEL_BOUNDARY_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")


def slugify_id(value: str) -> str:
    text = value.strip()
    text = CAMEL_BOUNDARY_1.sub(r"\1-\2", text)
    text = CAMEL_BOUNDARY_2.sub(r"\1-\2", text)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())
    return slug.strip("-")


def make_snapshot_tag(date_part: str, build_id: str) -> str:
    return f"{date_part}_build_{build_id}"