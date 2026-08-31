# MoACubed Project Plan

> **Status:** Planning and specification baseline
>
> **Goal:** Build three Hermes skills that collect human feedback, run targeted profile counterfactuals, and establish repeatable profile baselines while minimizing unnecessary model calls.

## 1. Scope

MoACubed evaluates complete Hermes profile configurations, not isolated models. Each result records the profile, provider/model, MoA aggregator and references, skills, tools, reasoning settings, fanout, iterations, verification evidence, and cost/latency signals.

The system consists of:

- `moaquery` (`moaq`): query the human after a completed MoA task.
- `moatesting` (`moat`): test a focused complaint or uncertainty against bounded candidate profiles and recommend routing.
- `moalevelset` (`moal`): run a fixed or user-supplied baseline task against profiles and compare each result with an explicit ideal.

## 2. Design principles

1. **Evidence before ranking.** Preserve objective verification, human judgement, and evaluator judgement as separate signals.
2. **Targeted replay.** If the human identifies one or two issues, test those issues rather than replaying the whole task.
3. **Token discipline.** Preflight profile distinctiveness before any model calls; pause on exact duplicates.
4. **Fair comparison.** Candidate profiles receive the same task, starting state, budget, acceptance checks, and isolation boundary.
5. **Iteration accountability.** Record productive, unproductive, and disproportionate work separately from raw iteration count.
6. **Append-only history.** Never silently rewrite historical evidence; supersede records explicitly.
7. **Recommendation before automation.** Initial releases recommend routing changes but do not apply them automatically.
8. **Profile-local state.** Keep each profile's MoACubed ledger and detailed records isolated under its Hermes home.

## 3. Target architecture

```text
MoACubed
├── shared contracts
│   ├── profile discovery and canonical fingerprinting
│   ├── distinctiveness preflight
│   ├── task and acceptance schema
│   ├── execution budget
│   ├── evidence and scoring schema
│   └── append-only record/ledger writer
├── moaq
│   └── trace → focused human review → review record
├── moat
│   └── review → issue extraction → bounded replay → verified recommendation
└── moal
    └── baseline fixture → isolated profile runs → verified comparison
```

The default/all-tools profile is the orchestrator for `moat` and `moal`. Candidate profiles must not see other candidates, human feedback, or evaluation framing.

## 4. Delivery phases

### Phase 0 — Contract and fixture

- Finalize `SPECIFICATION.md` schemas and state transitions.
- Define the standard UI/code baseline fixture and its ideal result.
- Confirm how Hermes profiles are launched, isolated, and stopped.
- Define verification adapters for shell, files, browser/UI, and external state.

**Exit criteria:** schemas validate; the fixture is deterministic; a profile can be launched in an isolated run directory.

### Phase 1 — Shared foundation

- Implement profile discovery without reading secrets.
- Canonicalize relevant profile configuration and calculate fingerprints.
- Implement exact/near-duplicate and task-relevance comparison.
- Implement preflight decisions and grouped user confirmation.
- Implement budget accounting and append-only JSONL records.
- Generate/update the human-readable `moacubed.md` ledger.

**Exit criteria:** duplicate profiles pause before model calls; distinct profiles proceed; records are reproducible and profile-local.

### Phase 2 — `moaq`

- Locate the latest completed MoA trace.
- Ask only the minimum structured human questions needed.
- Support turn-level and task-level reviews.
- Capture issue statements, severity, aggregator agreement, reference usefulness, and verification confidence.
- Write trace-linked review records.

**Exit criteria:** a human can review a completed turn/task, defer optional questions, and produce a valid review without contaminating the conversation transcript.

### Phase 3 — `moal`

- Implement standard and user-supplied baseline task loading.
- Materialize isolated candidate workspaces.
- Run candidates under identical budgets and acceptance checks.
- Capture model calls, tool calls, iterations, failures, and verification.
- Score against the frozen ideal and update the ledger.

**Exit criteria:** at least two genuinely different profiles can be compared, exact duplicates pause, and a failed/timeout run remains valid evidence.

### Phase 4 — `moat`

- Consume a `moaq` review and original trace.
- Classify each complaint as style, diagnosis, solution, implementation, completeness, safety, or verification.
- Select the smallest valid replay scope.
- Select a bounded, task-relevant candidate set.
- Run focused claim or implementation replays.
- Produce recommendation-only output with confidence, cost, and iteration analysis.

**Exit criteria:** a focused complaint does not trigger an unnecessary full replay; candidate outcomes are independently verified.

### Phase 5 — Analysis and calibration

- Aggregate scores by capability, profile, model, MoA team, and configuration fingerprint.
- Detect disproportionate iteration against comparable baselines.
- Estimate reference marginal value through sampled leave-one-out replay.
- Calibrate weights and thresholds only after minimum sample counts.
- Add repeatability runs and configuration-sensitivity analysis.

**Exit criteria:** recommendations show evidence, sample counts, uncertainty, and cost/quality tradeoffs.

### Phase 6 — Optional controlled automation

Only after offline validation:

- Recommend task-specific presets automatically.
- Require explicit approval before applying routing changes.
- Keep rollback and audit history.
- Never allow one anomalous run to alter global routing.

## 5. Planned artifacts

```text
moacubed/
├── PROJECT_PLAN.md
├── SPECIFICATION.md
├── schemas/                 # JSON Schema/YAML schema files, Phase 1
├── fixtures/                # frozen baseline tasks, Phase 0/3
├── tests/                   # contract and integration tests
└── docs/                    # implementation notes, if needed
```

Profile-local runtime state:

```text
$HERMES_HOME[/profiles/<name>]/
├── moacubed.md
└── moacubed-data/
    ├── reviews.jsonl
    ├── targeted-tests.jsonl
    ├── levelsets.jsonl
    ├── recommendations.jsonl
    └── preflight.jsonl
```

## 6. Validation plan

- Schema validation for every record.
- Unit tests for canonicalization, fingerprints, duplicate detection, scoring gates, and iteration classification.
- Integration tests for preflight confirmation and no-call-on-duplicate behavior.
- Fixture tests for deterministic acceptance checks.
- Failure tests for timeout, missing tool, failed test, malformed review, and unavailable reference model.
- Golden-file tests for ledger generation.
- Manual verification that traces/reviews do not enter the normal Hermes transcript.
- Cost accounting tests proving targeted replay stays within budget.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| False precision in evaluator scores | Store evidence, confidence, and `null`; retain score vectors. |
| Duplicate runs inflate confidence | Group by configuration fingerprint; label repeats as repeatability evidence. |
| Candidate contamination | Isolated workspaces and separate candidate sessions. |
| Human review fatigue | Focused questions, optional fields, task-level batching. |
| Over-penalizing hard debugging | Compare effort to task complexity and comparable history. |
| Judge preference replacing truth | Objective verification gates correctness and completion. |
| Token explosion | Preflight, bounded candidates, staged replay, early stopping, budgets. |
| Profile drift | Record fingerprints, Hermes version, baseline version, and staleness. |

## 8. Open implementation decisions

These must be resolved during Phase 0 before production implementation:

1. Exact Hermes invocation/API for launching another profile.
2. Whether candidate runs use subprocesses, worktrees, or both.
3. Browser/UI driver used by the standard fixture.
4. How a completed task boundary is detected for `moaq`.
5. Which evaluator model performs structured grading.
6. Default token, call, wall-time, and candidate-count budgets.
7. Whether skills are installed globally or bundled in a dedicated MoACubed project.
8. Exact slash-command registration mechanism for `moaq`, `moat`, and `moal`.

## 9. Definition of done for v1

- Three skills exist with the names and abbreviations above.
- All three perform distinctiveness preflight.
- Exact duplicates pause before token-spending work.
- `moaq` writes structured human feedback.
- `moat` performs focused, independently verified candidate tests.
- `moal` performs reproducible baseline runs.
- Every tested profile has a profile-local `moacubed.md` ledger.
- Model identity, MoA composition, fanout, cost, latency, and iteration behavior are recorded.
- Unproductive/disproportionate iteration affects efficiency/routing evidence.
- No automatic production routing changes occur in v1.
