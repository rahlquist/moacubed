# MoACubed runtime architecture options

## Executive summary

There are four viable implementation paths. The recommended starting point is **Option 2: a standalone MoACubed runner that owns the profile-aware MoA orchestration and delegates the aggregator's normal Hermes execution path**. It gives MoACubed control over persona-aware fanout without silently replacing Hermes internals.

If the goal is maximum native integration and the project can accept a Hermes core change, **Option 4** is the best long-term architecture. **Option 1** is the fastest experiment. **Option 3** is the most independent, but recreating the full Hermes agent loop is the highest-risk path.

## Comparison chart

| Option | Architecture | Profile-aware references | Full aggregator profile | Native Hermes agent loop | Maintenance burden | Main advantage | Main risk |
|---|---|---:|---:|---:|---:|---|---|
| **1. Skill-only orchestration** | `moaq`/`moat`/`moal` instruct the active agent to run candidate profiles | Yes, procedurally | Yes, by launching profiles | Yes, through normal Hermes processes | Low | Fastest proof of concept | Behavior depends on the acting model following the procedure consistently |
| **2. Standalone MoACubed runner** **(recommended first)** | Separate MoACubed runner owns fanout and invokes Hermes for the aggregator | Yes | Yes | Yes, if aggregator is delegated to a normal Hermes profile/process | Medium | Strong control without patching Hermes core | Process/context transfer and version coordination |
| **3. Static fork of `moa_loop.py`** | MoACubed copies and modifies Hermes' MoA loop | Yes | Potentially | Only if the fork reproduces or delegates the full loop | High | Maximum control over MoA behavior | Upstream drift and duplicated runtime logic |
| **4. Generic Hermes orchestration extension** | Hermes exposes a provider/plugin interface for agent orchestrators | Yes | Yes | Yes | Low after upstream seam exists | Cleanest native integration | Requires Hermes core design, implementation, review, and release coordination |

## Option 1 — Skill-only orchestration

### Shape

```text
Active Hermes agent
  ├── loads MoACubed skill
  ├── discovers candidate profiles
  ├── performs duplicate preflight
  ├── launches profiles with normal Hermes commands
  └── aggregates and records results
```

### Pros

- No Hermes core change.
- No fork to maintain.
- Uses existing profile, tool, skill, and session behavior.
- Lowest engineering cost.
- Good for validating the scoring model and task fixtures.
- Easy to keep recommendation-only and human-approved.

### Cons

- The active model must follow a long procedural workflow correctly.
- It is not a true replacement for native MoA.
- Fanout may be sequential or inconsistently implemented.
- Harder to guarantee identical prompt construction across runs.
- The aggregator is not automatically given a controlled profile-aware MoA context.
- Runtime metrics depend on subprocess output and trace parsing.

### Best use

Use this as the **data-collection and evaluation prototype**. It should remain available even after a runtime plugin exists because it is useful for baselines and regression checks.

## Option 2 — Standalone MoACubed runner

### Shape

```text
MoACubed runner
  ├── resolves aggregator profile
  ├── resolves reference profiles
  ├── loads and sanitizes reference SOUL.md files
  ├── runs reference calls with persona only
  ├── invokes the aggregator as a normal Hermes profile
  ├── preserves aggregator tools/skills/memory policy
  └── writes MoACubed traces and ledgers
```

### Reference context

```text
SOUL.md only
No tools
No skills
No memory
No MCP
No credentials
No claims of execution
```

### Aggregator context

```text
Full aggregator profile
Normal Hermes system and tools
Explicit MoACubed authority policy
Reference outputs appended as advisory guidance
```

### Pros

- Strong control over profile-aware fanout.
- References can receive distinct personas without receiving tools.
- Aggregator can retain the normal Hermes tool loop.
- Does not require modifying Hermes core.
- Static MoACubed behavior can be versioned independently.
- Easier to instrument with MoACubed-specific traces, scores, and routing.
- Can provide a native-mode compatibility switch.

### Cons

- Must define a reliable boundary between the runner and the aggregator.
- Process startup adds latency.
- Session, memory, interrupt, approval, and context transfer need explicit handling.
- Must track which Hermes version and profile APIs it supports.
- A subprocess-based aggregator may not share the exact parent conversation state without serialization.
- A long-running plugin process may need careful lifecycle management.

### Best use

Recommended first production architecture for MoACubed. Build it as an explicit runner or provider surface rather than an invisible monkey-patch of Hermes.

## Option 3 — Static fork of `moa_loop.py`

### Shape

```text
MoACubed plugin
  └── copied moa_loop.py
        ├── custom profile resolver
        ├── persona-aware references
        ├── custom aggregator context
        ├── custom traces
        └── custom routing
```

### Pros

- Maximum control over reference prompt construction.
- Can preserve native parallel fanout, trimming, caching, token accounting, and provider routing if copied accurately.
- Can implement profile-aware roles close to the native execution point.
- Static source gives MoACubed independence from upstream changes.

### Cons

- The copy will drift from Hermes.
- Security, privacy, caching, provider, and accounting fixes must be ported manually.
- A copied loop may still depend on private Hermes internals.
- It can accidentally fork only part of the behavior while appearing complete.
- Testing burden grows with every Hermes release.
- It may require a private integration seam or invasive runtime patching to become the active MoA implementation.
- Reproducing the full aggregator agent loop is difficult if the copied code only handles model calls.

### Best use

Use only when the standalone runner cannot provide the required execution semantics. Pin the fork to an exact Hermes commit and maintain an upstream-diff review process.

## Option 4 — Generic Hermes orchestration extension

### Shape

Hermes exposes a generic extension point, for example:

```python
ctx.register_orchestrator("moacubed", orchestrator)
```

MoACubed supplies the profile-aware implementation without copying the main agent loop.

### Pros

- Best native behavior and least long-term duplication.
- Hermes remains responsible for session state, tools, approvals, interrupts, caching, and provider resolution.
- MoACubed owns only profile selection, persona context, fanout policy, and evaluation metadata.
- Other orchestration plugins could reuse the same interface.
- Easier to test through a stable public contract.

### Cons

- Requires a Hermes core/API change.
- Must design a generic interface rather than a MoACubed-specific hook.
- Requires upstream review and release coordination.
- Cannot be delivered entirely inside the MoACubed repository initially.
- Compatibility with older Hermes versions requires a fallback path.

### Best use

Target architecture if MoACubed proves valuable and the runtime behavior is worth upstreaming.

## Decision matrix

Scoring: 1 = poor, 3 = acceptable, 5 = strong.

| Criterion | Option 1 skill-only | Option 2 standalone runner | Option 3 static fork | Option 4 Hermes extension |
|---|---:|---:|---:|---:|
| Speed to first experiment | **5** | 4 | 2 | 1 |
| Profile-persona control | 3 | **5** | **5** | **5** |
| Aggregator full-profile support | 4 | **5** | 3 | **5** |
| Native agent-loop fidelity | **5** via subprocess | 4 | 3 | **5** |
| Independence from Hermes internals | **5** | 4 | 1 | 3 |
| Runtime control | 2 | **5** | **5** | 4 |
| Upstream maintenance cost | **5** | 3 | 1 | 4 |
| Token/cost instrumentation | 3 | **5** | 5 | 4 |
| Isolation and safety | 4 | **5** | 3 | **5** |
| Long-term architectural quality | 3 | 4 | 2 | **5** |
| Total implementation risk | **Low** | **Medium** | **High** | **Medium/high initially** |

## Recommended sequence

### Phase A — Keep the current skills

Use `moaq`, `moat`, and `moal` to establish:

- Baseline tasks
- Human review records
- Profile fingerprints
- Iteration metrics
- Objective verification
- Initial routing evidence

### Phase B — Build Option 2

Create a standalone runner with:

1. Profile discovery and configuration fingerprinting.
2. Reference `SOUL.md` loading and sanitization.
3. Tool-free, skill-free, memory-free reference prompts.
4. Full-profile aggregator invocation.
5. Explicit aggregator authority policy.
6. Native-mode bypass.
7. MoACubed trace and cost accounting.
8. Compatibility tests against one pinned Hermes version.

### Phase C — Compare against native MoA

Run a controlled level set with:

```text
A. Native Hermes MoA
B. Persona-aware references
C. Full-profile aggregator + native references
D. Full-profile aggregator + persona-aware references
```

Compare verified quality, safety, cost, latency, and productive versus unproductive iteration.

### Phase D — Decide whether to fork further or upstream an extension

- If Option 2 is sufficient, keep it standalone.
- If it needs private Hermes internals, isolate the dependency behind adapters.
- If the behavior is broadly useful, propose Option 4 upstream.
- Use Option 3 only when a stable extension point cannot provide the needed behavior.

## Non-negotiable invariants

Regardless of the option:

- Reference profiles never receive tools, skills, memory, MCP access, or credentials.
- Reference personas are advisory data, not authority over Hermes policy.
- The aggregator remains responsible for tool execution and verification.
- Exact duplicate profiles pause before token-spending tests.
- Model identity and full configuration fingerprints are recorded.
- Human feedback, objective verification, and evaluator judgement remain separate.
- No automatic production routing changes in the first release.
- Static copies record the upstream Hermes commit they were copied from.
- Candidate profiles do not see other candidates or evaluation framing.
