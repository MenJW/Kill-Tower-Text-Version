from __future__ import annotations

import re


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."