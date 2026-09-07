# Option 2 implementation status

## Implemented

- Profile context loading and SOUL.md digesting.
- Persona sanitization for secret-shaped values.
- Reference and aggregator prompt construction with authority boundaries.
- Bounded parallel reference orchestration API.
- Fanout cadence validation (`user_turn`, `per_iteration`, `every_n:N`).
- Normal Hermes subprocess boundary for the full-profile aggregator.
- Append-only aggregator-owned profile-aware MoA trace storage with explicit role metadata and a compact derived cross-context index.
- Explicit `moacubed-moa` CLI entry point.
- Temporary-Hermes-home unit/integration coverage.

## Current limitation

The first slice does not yet include a direct provider adapter for reference model calls. Until that adapter is implemented, reference slots are recorded as `blocked: no reference caller configured`; the aggregator still runs through a real Hermes profile subprocess. This is deliberate: no fake reference output is generated.

## Next implementation slice

Implement `reference_runtime.py` with a Hermes-compatible direct model-call adapter, preserving the no-tools/no-skills/no-memory/no-MCP contract. Then add a real two-profile smoke test where one reference produces advisory output and the aggregator receives it.
