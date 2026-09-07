from __future__ import annotations
import argparse
from pathlib import Path
from .profile_context import load_profile_context
from .profile_moa import MoAOptions, run_profile_aware_moa
from .aggregator_runtime import run_aggregator_profile
from .trace_records import build_context_metadata, write_aggregator_record, write_derived_index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run profile-aware MoACubed fanout")
    parser.add_argument("--aggregator-profile", required=True)
    parser.add_argument("--reference-profile", action="append", required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--fanout", default="user_turn")
    parser.add_argument("--reference-max-tokens", type=int, default=600)
    args = parser.parse_args(argv)
    options = MoAOptions(fanout=args.fanout, reference_max_tokens=args.reference_max_tokens)
    task = args.prompt_file.read_text(encoding="utf-8")
    result = run_profile_aware_moa(
        task, args.aggregator_profile, args.reference_profile, options,
        aggregator_caller=lambda profile, prompt, opts: run_aggregator_profile(profile, prompt, args.workspace, opts),
    )
    agg = load_profile_context(result.aggregator_profile)
    refs = [load_profile_context(name) for name in result.reference_profiles]
    record = {
        "run_id": result.run_id,
        "runtime_mode": options.native_compatibility_label,
        "task_id": args.prompt_file.stem,
        "context": build_context_metadata(
            agg.short_identity,
            [{**ref.short_identity, "persona_only": True, "tools": False, "skills": False, "memory": False, "mcp": False} for ref in refs],
            {"fanout": options.fanout, "reference_max_tokens": options.reference_max_tokens},
        ),
        "status": result.status,
        "references": [r.__dict__ for r in result.references],
        "aggregator_response": result.aggregator_response[-20000:],
        "error": result.error,
    }
    path = write_aggregator_record(args.aggregator_profile, record)
    write_derived_index(record)
    print(f"run_id: {result.run_id}\nstatus: {result.status}\ntrace: {path}")
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
