# Kill Tower Text Version

Kill Tower Text Version is a Python-first scaffold for a text-based implementation of Slay the Spire 2.

The current repository contains:

- a Python package layout under src/
- a Typer CLI entry point
- a minimal Textual application shell
- data schemas and loading utilities
- snapshot import and normalization script templates
- baseline docs for architecture, parity, combat flow, and TUI flow

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
kill-tower info
kill-tower run ui
```

## Common Commands

```bash
kill-tower info
kill-tower data paths
kill-tower data init-manifest
kill-tower run ui
python scripts/smoke_run.py
python scripts/generate_unresolved_coverage_report.py 2026-04-09_build_unknown
python scripts/generate_transcript_goldens.py
pytest
```

## Repository Layout

- docs/: architecture and delivery notes
- data/: raw imports, normalized snapshots, reports
- scripts/: import, normalization, diff, and smoke-run helpers
- src/kill_tower/: package source
- tests/: unit, integration, parity, regression, golden suites

## Roadmap

The detailed roadmap lives in todo.md.