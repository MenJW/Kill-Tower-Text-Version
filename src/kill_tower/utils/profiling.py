from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator


@contextmanager
def timed_section() -> Iterator[float]:
    start = perf_counter()
    yield start
    _ = perf_counter() - start