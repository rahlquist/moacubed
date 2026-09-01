---
name: moaquery
description: "Collect focused human feedback after a completed MoA task."
version: 0.1.0
author: Richard (rahlquist), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [moacubed, moa, review, feedback, evaluation]
    related_skills: [moatesting, moalevelset]
---

# MoAQuery

Collect human-grounded feedback on a completed MoA turn or task. Store the review separately from the conversation transcript and link it to the source trace.

## When to Use

- A completed MoA turn or task needs human review.
- The user wants to identify useful, misleading, or missing advice.
- A later targeted test needs a concrete complaint.

## Procedure

1. Locate the selected completed MoA trace under `$HERMES_HOME/moa-traces/`. If more than one plausible trace exists, ask the user to select one.
2. Read only the trace metadata and relevant outputs needed for review. Do not expose secrets or unnecessarily repeat full trace content.
3. Summarize the preset, aggregator, references, tool activity, and task boundary.
4. Ask focused questions:
   - Was the final result accepted, partially accepted, rejected, or unclear?
   - Which references were helpful?
   - Which references were irrelevant or misleading?
   - Did the aggregator synthesize well, ignore useful advice, follow bad advice, or fail independently?
   - What verification evidence exists?
   - What specifically should have been different?
5. Extract zero or more concrete issues. Each issue has an ID, statement, target, category, severity, aggregator agreement, and evidence.
6. Write one append-only review record to the active profile's `moacubed-data/reviews.jsonl` using the repository's `RecordWriter`.
7. Regenerate the active profile's `moacubed.md` ledger.
8. Report the review ID, issue count, evidence state, and whether `moatesting` is warranted.

## Record Contract

Use these controlled values:

- Outcome: `accepted`, `partially_accepted`, `rejected`, `unclear`, `not_applicable`.
- Reference label: `helpful`, `partially_helpful`, `neutral`, `misleading`, `not_relevant`, `not_reviewed`.
- Aggregator label: `synthesized_well`, `ignored_useful_advice`, `followed_bad_advice`, `overrode_good_advice_correctly`, `failed_independently`, `unclear`.
- Verification: `objective_pass`, `objective_fail`, `human_accepted`, `human_rejected`, `unverified`.

Do not force numeric ratings when the user has only one specific complaint. Preserve human comments verbatim except for secrets and privacy-sensitive material.

## Guardrails

- Do not invent trace metadata.
- Do not treat human acceptance as objective verification.
- Do not infer that a bad final result makes every reference bad.
- Do not write reviews into ordinary session history.
- Use `$HERMES_HOME`; never assume a machine-local path.

## Verification

Confirm that the new JSONL record parses, contains the source trace ID and required human fields, and that the profile ledger was regenerated.