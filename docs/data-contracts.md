# Data Contracts

## Snapshot Layout

```text
data/
  raw/
    spire_codex/<snapshot_tag>/<lang>/<entity>.json
    kotone_reference/<snapshot_tag>/index.html
  normalized/
    <snapshot_tag>/<lang>/<entity>.json
  reports/
    <snapshot_tag>/gap-report.md
```

## Required Manifest Fields

- game
- app_id
- game_version
- build_id
- snapshot_tag
- fetched_at
- sources
- counts

## Entity Rules

- Every entity has a stable internal id.
- Cross-language data shares the same internal id.
- Source metadata is preserved for audits.
- Runtime-only fields are added during normalization, not in raw imports.

## Validation Rules

- No duplicate ids per entity type
- No missing required localized names
- No broken cross references
- Manifest counts must match on-disk files when data is considered complete