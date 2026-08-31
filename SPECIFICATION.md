# MoACubed Specification

**Status:** Draft v0.1

## 1. Purpose and terminology

MoACubed is a three-skill evaluation system for Hermes profiles and MoA configurations.

- **Profile:** An isolated Hermes configuration, including its instructions, skills, memory, tools, provider/model, and runtime settings.
- **MoA team:** Reference models plus one aggregator used for a model iteration.
- **Run:** One isolated execution of one profile/configuration against one task.
- **Review:** Human feedback linked to a completed MoA trace.
- **Issue:** A concrete complaint or uncertainty extracted from a review.
- **Baseline:** A versioned task with a frozen ideal and acceptance checks.
- **Configuration group:** Runs sharing the same canonical configuration fingerprint.

## 2. Skills

### 2.1 `moaquery` / `moaq`

**Input:** completed MoA trace and optional task boundary.

**Behavior:**

1. Locate the completed trace.
2. Run distinctiveness preflight if profile comparison is requested.
3. Ask focused human questions; do not force irrelevant scoring.
4. Capture final outcome, useful/misleading references, aggregator behavior, concrete issues, severity, and verification state.
5. Write an append-only review record outside the normal transcript.

**Output:** review ID, stored record path, extracted issues, and whether `moat` is recommended.

### 2.2 `moatesting` / `moat`

**Input:** review ID, trace ID, or explicit issue.

**Behavior:**

1. Load review and trace.
2. Extract one or more concrete issues.
3. Determine aggregator agreement: `agreed`, `disagreed`, or `unclear`.
4. Choose the smallest valid scope: `none`, `claim`, `focused_candidate`, or `full_replay`.
5. Select bounded, task-relevant candidates.
6. Run distinctiveness preflight before model calls.
7. Pause on exact duplicates; warn and proceed on near duplicates.
8. Run isolated candidates under equal budgets.
9. Verify each result.
10. Recommend routing; do not modify production routing in v1.

**Output:** targeted test records and recommendation record.

### 2.3 `moalevelset` / `moal`

**Input:** standard baseline or user-supplied baseline.

**Behavior:**

1. Load a versioned task, ideal, effort expectations, and acceptance checks.
2. Discover requested profiles/configurations.
3. Run distinctiveness preflight.
4. Pause on exact duplicates before spending tokens.
5. Materialize isolated run state for each candidate.
6. Execute the same task and acceptance checks.
7. Capture outcome, verification, cost, latency, and iteration details.
8. Score each profile and update its ledger.

**Output:** level-set run set, comparison report, and profile-ledger updates.

## 3. State and storage

Use `$HERMES_HOME`, never a hardcoded home. For profile `default`, store at `$HERMES_HOME/moacubed.md`; for another profile, store at `$HERMES_HOME/profiles/<name>/moacubed.md`.

Detailed records live beside the ledger:

```text
moacubed-data/
├── reviews.jsonl
├── targeted-tests.jsonl
├── levelsets.jsonl
├── recommendations.jsonl
└── preflight.jsonl
```

Records are append-only. Corrections create a new record with `supersedes`; old records remain auditable.

## 4. Common run identity

Every run must record:

```yaml
run_id: unique string
created_at: RFC3339 UTC
profile: profile name
configuration_group: canonical fingerprint group
configuration_fingerprint: sha256 digest
hermes_version: exact version or null
task_id: task/baseline ID
trace_id: source MoA trace or null
purpose: levelset | targeted_test | repeatability
```

Configuration identity must include, where applicable:

```yaml
configuration:
  profile: name
  provider: provider
  model: model
  reasoning_effort: value or null
  skills: canonical list
  tools: canonical permissions list
  mcp_servers: canonical list
  memory_scope: identifier/summary, never secret contents
  system_instruction_digest: digest
  moa:
    enabled: boolean
    preset: name or null
    aggregator: {provider, model, reasoning_effort}
    references: [{slot, provider, model, reasoning_effort}]
    fanout: user_turn | per_iteration | every_n:N
    reference_max_tokens: integer or null
```

Do not store credentials, API keys, raw `.env` values, or secret-bearing memory in MoACubed records.

## 5. Distinctiveness preflight

Preflight occurs before any candidate model/tool execution.

### 5.1 Comparison classes

- `meaningful_difference`: proceed.
- `near_duplicate`: warn; proceed unless policy says otherwise.
- `irrelevant_difference`: warn; proceed for a task where the difference is not relevant.
- `exact_duplicate`: pause and request confirmation.

Compare canonical substantive content, not names, timestamps, ordering, comments, or formatting. The comparison must be task-relevant for `moat`.

### 5.2 Exact duplicate behavior

If a candidate has the same substantive configuration fingerprint as another candidate:

```text
Exact duplicate detected: <candidate> == <existing>
No comparative profile evidence will be gained. Run anyway as a repeatability test?
```

Required action: `pending_confirmation` → `run`, `skip`, or `cancel`.

Grouped duplicate confirmation is permitted for `moal`. A user may intentionally run duplicates for nondeterminism/repeatability; mark the purpose accordingly and do not count repeats as independent profile designs.

Preflight records must include candidates, similarities, differences, decision, and confirmation.

## 6. Task/baseline schema

A baseline is versioned and immutable after execution:

```yaml
schema_version: 1
id: ui-code-standard
version: v1
title: Small UI and code task
workspace_fixture: path or fixture identifier
prompt: task text
ideal:
  functional_requirements:
    - id: persistence
      description: count survives refresh
  allowed_implementations: multiple_valid
  scope_constraints:
    - no unrelated dependency changes
acceptance:
  - id: tests
    type: command
    command: pytest -q
    expected_exit_code: 0
  - id: browser_behavior
    type: browser
    assertions: []
  - id: changed_scope
    type: files
    assertions: []
effort_expectations:
  complexity: trivial | low | medium | high
  target_iterations: integer
  acceptable_max_iterations: integer
  problems:
    - id: persistence
      complexity: medium
      target_iterations: 4
      acceptable_max_iterations: 8
budget:
  max_profiles: integer
  max_agent_iterations: integer
  max_model_calls: integer
  max_tool_calls: integer
  max_wall_time_seconds: integer
  max_output_tokens: integer
```

User-supplied tasks are separate IDs/versions. Never overwrite the standard baseline.

## 7. Review schema

```yaml
schema_version: 1
review_id: id
trace_id: id
profile: name
scope: turn | task
created_at: RFC3339
human:
  final_outcome: accepted | partially_accepted | rejected | unclear | not_applicable
  aggregator_feedback: synthesized_well | ignored_useful_advice | followed_bad_advice | overrode_good_advice_correctly | failed_independently | unclear
  reference_feedback:
    - slot: integer
      label: helpful | partially_helpful | neutral | misleading | not_relevant | not_reviewed
      comment: optional
  issues:
    - issue_id: id
      statement: concrete complaint
      target: reference | aggregator | tool_execution | final_outcome
      category: style | diagnosis | solution | implementation | completeness | safety | verification | efficiency
      severity: cosmetic | minor | major | critical
      aggregator_agreement: agreed | disagreed | unclear
      evidence: list
  verification: objective_pass | objective_fail | human_accepted | human_rejected | unverified
  comment: optional
```

## 8. Run result schema

```yaml
schema_version: 1
run_id: id
configuration: {see common run identity}
status: passed | partial | failed | timeout | blocked | unavailable
started_at: RFC3339
finished_at: RFC3339
outcome:
  correctness: score/confidence/evidence
  completeness: score/confidence/evidence
  verification: score/confidence/evidence
  safety: score/confidence/evidence
  human_alignment: score/confidence/evidence
  robustness: score/confidence/evidence
  tool_orchestration: score/confidence/evidence
  communication: score/confidence/evidence
  ui: {functionality, visual_quality, accessibility}
  code: {quality, test_quality}
efficiency:
  wall_clock_seconds: number
  input_tokens: integer or null
  output_tokens: integer or null
  model_call_count: integer
  reference_call_count: integer
  aggregator_call_count: integer
  tool_call_count: integer
  agent_loop_iterations: integer
  productive_iterations: integer
  unproductive_iterations: integer
  disproportionate_iterations: integer
  failed_attempts: integer
  rework_iterations: integer
  first_pass_success: boolean or null
  iteration_anomaly: none | warning | major | critical
problems:
  - problem_id: id
    category: category
    iterations:
      diagnosis: integer
      implementation: integer
      verification: integer
      rework: integer
      total: integer
    productive: integer
    unproductive: integer
    outcome: resolved | unresolved | not_applicable
verification_evidence: list
flags: list
```

Each score is `{score: 0.0..1.0|null, confidence: low|medium|high|none, evidence: [...]}`. `null` means unknown; it is not failure.

## 9. Scoring and weights

Store the weights used with every result. Initial engineering weights:

```yaml
correctness: 0.30
completeness: 0.15
verification: 0.25
safety: 0.15
human_alignment: 0.05
efficiency: 0.10
```

Efficiency is a vector, not raw iteration count:

```yaml
productive_progress: 0.25
iteration_discipline: 0.30
disproportionate_effort: 0.25
wall_clock: 0.10
cost: 0.05
tool_call_efficiency: 0.05
```

Safety and correctness gates apply before aggregate utility:

- safety below 0.50 → `unsafe`
- correctness below 0.50 → `failed`
- verification below 0.40 → `unverified`
- completeness below 0.50 → `incomplete`

Unproductive and disproportionate iterations reduce efficiency and create routing flags; necessary productive debugging does not receive the same penalty.

Weights are policy defaults. Profile-specific adjustments require at least five comparable tasks, at least three flagged examples for an iteration adjustment, matching task domain, and recorded rationale.

## 10. Iteration accounting

An agent-loop iteration is a model/tool cycle. Record MoA calls separately because one iteration can contain multiple reference calls plus one aggregator call.

Classify each iteration as:

- `productive`: new evidence, valid implementation, useful test, verification, or legitimate recovery.
- `unproductive`: repeated inspection, unchanged retry, ignored output, circular reasoning, needless refactor, or premature claim.
- `disproportionate`: effort materially above the target for comparable task complexity.

Use task-specific expectations and historical comparable runs. Do not apply a universal penalty such as `iterations × constant`.

## 11. Targeted testing rules

`moat` must map each issue to a minimum test:

| Issue | Minimum scope |
|---|---|
| style only | no replay; record preference |
| disputed claim | claim evaluation |
| candidate diagnosis/solution | focused candidate comparison |
| implementation defect | isolated focused implementation replay |
| interacting/multi-part failure | full replay |

If the aggregator agreed with the human’s diagnosis, test remediation rather than rediscovering diagnosis. If it disagreed, test the disputed claim first.

Candidate selection includes the original baseline, relevant historically strong profiles, and at most one exploratory candidate unless the issue is critical or evidence is inconclusive.

## 12. Level-set rules

The standard baseline should contain a small UI/code task with explicit acceptance checks and reasonable effort targets. Each candidate receives the same starting fixture, prompt, budget, environment, and verification commands in an isolated workspace.

The ideal must be frozen before candidate results are inspected. Multiple valid implementations are acceptable. A timeout, missing tool, or failed test is a real result.

Baseline results are capability evidence, not a universal profile ranking. Record repeatability separately when identical configurations are intentionally rerun.

## 13. Ledger requirements

Each tested profile has `moacubed.md` with:

- identity and configuration fingerprint
- current domain-specific weights
- capability summary with score, confidence, and sample count
- level-set results
- targeted tests
- MoA reference/aggregator performance
- iteration performance and flags
- human feedback summary
- routing recommendations and status

The ledger is human-readable; JSONL records are authoritative for aggregation. Historical entries are never silently deleted.

## 14. Privacy, isolation, and failure handling

- Do not read or emit secrets.
- Apply Hermes privacy filtering to trace-derived content.
- Keep candidate outputs and reviews outside the conversation transcript.
- Candidate profiles do not see comparison data.
- One failed reference does not invalidate a MoA turn; record the failure.
- One failed candidate does not abort the run set.
- Stop before model calls when exact-duplicate confirmation is pending.
- Stop when budget is exhausted and mark the run `timeout` or `blocked`, not successful.

## 15. Recommendation schema

```yaml
schema_version: 1
recommendation_id: id
created_at: RFC3339
domain: task capability
scope: targeted | levelset | aggregate
candidates: [profile/configuration groups]
preferred_configuration: id or null
classification: better | same_lower_cost | same_lower_latency | worse | uncertain
quality_comparison: vector
cost_comparison: vector
iteration_comparison: vector
evidence_run_ids: []
sample_count: integer
confidence: low | medium | high
status: proposed | accepted | rejected | superseded | stale
rationale: text
```

No recommendation may be applied automatically in v1.

## 16. Standard baseline seed

The initial standard baseline should be a tiny local web application task requiring:

1. Diagnose a deliberately planted persistence bug.
2. Fix the code.
3. Add a regression test.
4. Make the displayed value visibly distinct.
5. Run automated tests.
6. Verify the UI behavior after refresh.
7. Report files changed and evidence.

The fixture, exact bug, UI assertion, and verification commands must be created and reviewed in Phase 0. The baseline version is immutable once used.
