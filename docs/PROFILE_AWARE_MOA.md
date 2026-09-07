# Profile-aware MoA

MoACubed's Option 2 runner is an explicit, standalone alternative to native Hermes MoA. It does not modify Hermes core or replace `agent/moa_loop.py`.

## Roles

- **Aggregator:** a normal Hermes profile. It retains its `SOUL.md`, skills, tools, memory policy, provider/model, and normal Hermes tool loop.
- **References:** persona-only advisory perspectives. They receive sanitized `SOUL.md` data and task context, but no tools, skills, memory, MCP servers, credentials, or execution authority.

Reference outputs are advisory. The aggregator remains responsible for resolving disagreement, performing work, and verifying the result.

## Invocation

```text
moacubed-moa \
  --aggregator-profile default \
  --reference-profile research \
  --reference-profile security \
  --prompt-file task.txt \
  --workspace /path/to/workspace
```

The command writes a profile-local `profile-moa.jsonl` trace and returns a nonzero exit code when the aggregator is blocked, times out, or fails.

## Compatibility boundary

The runner currently uses the normal `hermes chat -q --profile --max-turns` subprocess contract for the aggregator. It is intentionally explicit and opt-in; native Hermes MoA remains unchanged.
