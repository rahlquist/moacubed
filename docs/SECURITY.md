# MoACubed security boundaries

## Reference profiles are untrusted advisory data

A reference `SOUL.md` is sanitized and wrapped as data. It does not override Hermes policy, user requirements, aggregator instructions, approvals, or verification requirements.

Reference calls receive:

- no tools;
- no skills;
- no memory;
- no MCP servers;
- no credentials;
- no write-capable workspace;
- no other reference outputs.

Reference outputs are likewise advisory data to the aggregator.

## Secrets and records

MoACubed does not persist API keys, `.env` values, credentials, or raw secret-bearing memory. Persona and output surfaces are redacted before persisted trace records according to the run privacy mode.

## Isolation

Each candidate run gets its own workspace/session boundary. Candidate profiles do not see other candidates, human review, or evaluation framing. Exact duplicate configurations are blocked before model calls unless the user explicitly requests a repeatability run.

## Aggregator authority

The aggregator is the only model that can perform the task. It retains normal Hermes tool and approval policy. MoACubed does not grant extra tools or silently modify Hermes core.

## Input paths

User-supplied prompt and workspace paths must be resolved and checked by the runner before use. Do not permit a task prompt to choose a trace destination or escape the configured run root.
