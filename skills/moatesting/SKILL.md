---
name: moatesting
description: "Test focused issues across profiles and recommend routing."
version: 0.1.0
author: Richard (rahlquist), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [moacubed, moa, testing, counterfactual, routing]
    related_skills: [moaquery, moalevelset]
---

# MoATesting

Run bounded counterfactual tests against candidate Hermes profiles for a concrete complaint or uncertainty. Recommend routing; do not change production routing automatically.

## When to Use

- `moaquery` produced a concrete issue.
- The user asks whether another profile would have done better.
- A narrow capability needs verified comparison.

## Procedure

1. Load the review and source trace, or structure the user's explicit issue.
2. Record target, category, severity, aggregator agreement, accepted requirements, and available evidence.
3. Select the smallest valid scope:
   - style-only: record preference; no replay;
   - disputed claim: claim evaluation;
   - diagnosis or solution: focused candidate comparison;
   - implementation defect: isolated focused implementation;
   - interacting failures: full replay.
4. If the aggregator agreed with the human's diagnosis, test remediation rather than rediscovering diagnosis.
5. Select a bounded candidate set: original baseline, relevant specialists, historically strong profiles, and at most one exploratory candidate.
6. Run distinctiveness preflight before any model calls. Exact duplicates pause for explicit confirmation; near duplicates warn and proceed.
7. Give candidates the same focused prompt, starting state, acceptance evidence, and budget in isolated workspaces. Candidates must not see other candidates, human feedback, or evaluation framing.
8. Capture model/provider identity, MoA team, fanout, model calls, tool calls, wall time, total iterations, productive iterations, unproductive iterations, rework, and disproportionate effort.
9. Verify the disputed point and preserve previously accepted behavior. A timeout, missing tool, or failed verification is a real outcome.
10. Compare correctness, verification, safety, effort quality, latency, and token/model-call cost.
11. Write append-only targeted-test and recommendation records. Regenerate affected profile ledgers.
12. Recommend `better`, `same_lower_cost`, `same_lower_latency`, `worse`, or `uncertain`, with evidence, sample count, confidence, and no automatic application.

## Iteration Rules

Necessary investigation is not penalized. Flag repeated inspections, unchanged retries, ignored tool output, circular reasoning, needless refactoring, premature completion, excessive rework, and effort disproportionate to task complexity.

## Guardrails

- Never replay the full task for a narrow issue unless interactions make isolation invalid.
- Never attribute a result to a profile without recording its model and configuration fingerprint.
- Never let duplicate runs inflate independent-profile confidence; group them by fingerprint.
- Never treat an evaluator opinion as objective verification.
- Do not expose secrets from traces or profile configuration.

## Verification

Confirm targeted records and recommendation records parse, reference every candidate run, include evidence and confidence, and that the recommendation is stored as `proposed` rather than applied automatically.
