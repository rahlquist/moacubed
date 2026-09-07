# MoACubed storage model

## Ownership rule

MoA results are **aggregator-owned** because reference usefulness and final quality depend on the aggregator's profile, model, skills, tools, persona, and synthesis behavior.

Primary profile-aware MoA storage:

```text
$HERMES_HOME[/profiles/<aggregator>]/
├── moacubed.md
└── moacubed-data/
    └── profile-moa.jsonl
```

Standalone acting-profile baseline results remain profile-owned:

```text
$HERMES_HOME[/profiles/<profile>]/moacubed-data/levelsets.jsonl
```

## Role metadata

Every profile-aware MoA record must identify:

```yaml
context:
  aggregator:
    profile: default
    model: provider:model
    soul_digest: sha256
    configuration_fingerprint: sha256
  references:
    - profile: research
      model: provider:model
      soul_digest: sha256
      persona_only: true
      tools: false
      skills: false
      memory: false
      mcp: false
  moa:
    preset: name
    fanout: user_turn
    reference_max_tokens: 600
```

The key unit is:

```text
aggregator × reference team × task class × configuration × verification outcome
```

Do not collapse a reference profile into a universal score. The same reference can be useful with one aggregator and unhelpful with another.

## Derived index

A compact, output-free cross-context index is stored under:

```text
$HERMES_HOME/moacubed-index/profile-performance.jsonl
```

It contains IDs, profiles, task IDs, status, scores, and configuration groups, but not raw prompts, personas, credentials, or model output.

This index supports cross-aggregator analysis without replacing the aggregator-local evidence.
