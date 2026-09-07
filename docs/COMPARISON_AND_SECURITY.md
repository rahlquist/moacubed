# Comparison and security status

## Runtime comparison

`moacubed.comparison` compares native and profile-aware modes using verified score, verification, latency, and model-call metadata. It does not rank unknown or blocked results as successes.

Supported labels:

- `native_moa`
- `persona_references`
- `full_profile_aggregator`
- `profile_aware_full`

## Security boundary

Reference profiles are advisory data only. They receive no tools, skills, memory, MCP servers, credentials, or write-capable workspace. Their `SOUL.md` content is sanitized before prompt injection and wrapped with explicit data delimiters.

The aggregator retains normal Hermes profile behavior and is responsible for actual execution and verification.

## Smoke-test result

The live two-profile path was exercised with `default` as aggregator and `research` as reference. The aggregator path passed. The reference bridge reached Hermes' provider runtime, but the configured `tencent/hy3:free` model returned HTTP 404 because its free period ended. The failure was recorded; no fake advisory output was substituted.
