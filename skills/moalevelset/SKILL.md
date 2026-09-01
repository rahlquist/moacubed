---
name: moalevelset
description: "Run baseline tasks against Hermes profiles."
version: 0.1.0
author: Richard (rahlquist), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [moacubed, moa, baseline, levelset, profile-testing]
    related_skills: [moaquery, moatesting]
---

# MoALevelSet

Run a frozen standard or user-supplied baseline against Hermes profiles under identical conditions. Compare each result with an explicit ideal and record evidence in the profile ledger.

## When to Use

- Profiles need a repeatable capability baseline.
- The user wants a head-to-head profile comparison.
- The user supplies a replacement baseline task.

## Procedure

1. Load the immutable baseline task, ideal, acceptance checks, effort expectations, and execution budget. The standard fixture is `ui-code-standard-v1`; a user-supplied task gets its own ID/version and never overwrites the standard.
2. Discover the requested profiles. Record complete configuration identity: profile, provider, model, reasoning effort, skills, tools, MCP servers, memory scope, system-instruction digest, MoA aggregator/references, fanout, and reference token cap.
3. Run distinctiveness preflight before model execution. Compare substantive, task-relevant configuration. Proceed on meaningful or near differences; pause on exact duplicates and offer `skip_duplicates`, `run_all`, or individual selection. Record the decision.
4. Materialize a clean isolated workspace per candidate. Candidates share no files, outputs, human feedback, or evaluation framing.
5. Launch each profile with the same task prompt and budget. Capture start/end times, final response, model calls, reference calls, aggregator calls, tool calls, output tokens, and every agent-loop iteration.
6. Classify iterations as productive, unproductive, or disproportionate. Compare effort with the baseline's complexity-specific target. Do not penalize necessary debugging like repeated work on a genuinely hard defect.
7. Run every acceptance check. Use command checks for tests/builds, browser checks for UI behavior, file checks for artifacts/scope, and explicit external-state readback where relevant.
8. Score the result vector: correctness, completeness, verification, safety, human alignment, efficiency, robustness, tool orchestration, communication, plus UI/code dimensions when relevant. Apply safety/correctness/verification/completeness gates before calculating utility.
9. Write an append-only level-set record to the active profile's `moacubed-data/levelsets.jsonl` and regenerate its `moacubed.md` ledger.
10. Compare profiles by verified quality first, then safety, effort discipline, latency, and cost. Report `better`, `equivalent`, `same_lower_cost`, `same_lower_latency`, `worse`, or `uncertain`; include sample count and confidence.

## Iteration Accounting

Record `agent_loop_iterations`, `problem_resolution_iterations`, `productive_iterations`, `unproductive_iterations`, `disproportionate_iterations`, `failed_attempts`, `rework_iterations`, `first_pass_success`, and `iteration_anomaly`. A successful but disproportionately expensive result is still valid, but should not be preferred for that task class.

## Guardrails

- Do not alter the baseline ideal after seeing candidate results.
- Do not mark timeouts, missing tools, or failed verification as success.
- Do not count identical configurations as independent profile designs; label intentional repeats as repeatability tests.
- Do not expose secrets or raw credential-bearing configuration.
- Do not automatically change routing in v1.

## Verification

Confirm every candidate has a run record, every acceptance check has pass/fail/unknown evidence, duplicate decisions are recorded, profile ledgers are regenerated, and the comparison report matches the persisted run set.
