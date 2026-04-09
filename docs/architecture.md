# Architecture

## Goal

Keep data ingestion, runtime simulation, and terminal presentation separated from the start.

## Layers

1. Raw data import
2. Normalized snapshot storage
3. Runtime simulation engine
4. Terminal UI
5. Replay, parity, and reporting

## Initial Boundaries

- Runtime code must not fetch remote data directly.
- UI code must not implement game rules.
- Snapshot tags are the boundary for version parity.
- Entity ids are stable internal keys and must not depend on localized names.

## Milestone-1 Scope

- Build a reproducible snapshot manifest
- Load normalized content from disk
- Run a minimal deterministic combat loop
- Surface the state in a Textual shell

## Open Questions

- Which STS2 build becomes the v1 parity target?
- Which data gaps require handwritten scripts instead of schema-driven behavior?
- Which systems are explicitly deferred until after the single-player vertical slice?