from __future__ import annotations
import argparse
from pathlib import Path
from .profile_moa import MoAOptions, run_profile_aware_moa
from .aggregator_runtime import run_aggregator_profile
from .trace_records import write_profile_moa_trace


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
    result = run_profile_aware_moa(task, args.aggregator_profile, args.reference_profile, options,
                                   aggregator_caller=lambda profile, prompt, opts: run_aggregator_profile(profile, prompt, args.workspace, opts))
    record = {"run_id": result.run_id, "runtime_mode": options.native_compatibility_label,
              "aggregator_profile": result.aggregator_profile, "reference_profiles": result.reference_profiles,
              "status": result.status, "references": [r.__dict__ for r in result.references],
              "aggregator_response": result.aggregator_response[-20000:], "error": result.error}
    path = write_profile_moa_trace(args.aggregator_profile, record)
    print(f"run_id: {result.run_id}\nstatus: {result.status}\ntrace: {path}")
    return 0 if result.status == "passed" else 1

if __name__ == "__main__":
    raise SystemExit(main())
