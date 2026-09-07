# Option 2 implementation status

## Implemented

- Profile context loading and SOUL.md digesting.
- Persona sanitization for secret-shaped values.
- Reference and aggregator prompt construction with authority boundaries.
- Bounded parallel reference orchestration API.
- Real Hermes auxiliary-client reference adapter using `task="moa_reference"` and `tools=None`.
- Fanout cadence validation (`user_turn`, `per_iteration`, `every_n:N`).
- Hard reference-count and duplicate-configuration checks before calls.
- Normal Hermes subprocess boundary for the full-profile aggregator.
- Append-only aggregator-owned profile-aware MoA trace storage with explicit role metadata and a compact derived cross-context index.
- Profile-aware MoA results in the human-readable ledger.
- Explicit `moacubed-moa` CLI entry point.
- Temporary-Hermes-home unit/integration coverage.

## Current limitation

The direct reference adapter is now implemented and covered by adapter tests. A live reference smoke test still depends on the active Hermes process environment having a usable provider/model route for the selected reference profile. No fake reference output is generated when that route is unavailable.

## Next implementation slice

Run the live two-profile smoke test, then add native-vs-profile-aware comparison records, skill integration, and security hardening.
