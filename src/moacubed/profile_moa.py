"""Standalone profile-aware MoA orchestration."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from .profile_context import ProfileContext, load_profile_context
from .persona_prompt import reference_prompt, aggregator_prompt
from .reference_runtime import call_reference

@dataclass
class MoAOptions:
    fanout: str = "user_turn"
    max_reference_workers: int = 4
    reference_max_tokens: int = 600
    reference_timeout_seconds: int = 120
    aggregator_max_turns: int = 20
    aggregator_timeout_seconds: int = 1200
    max_total_model_calls: int = 40
    max_total_output_tokens: int = 12000
    max_reference_profiles: int = 4
    privacy_mode: str = "full"
    native_compatibility_label: str = "profile-aware-v1"

    def validate(self) -> None:
        if self.fanout != "user_turn" and self.fanout != "per_iteration" and not (self.fanout.startswith("every_n:") and int(self.fanout.split(":", 1)[1]) >= 2):
            raise ValueError(f"invalid fanout: {self.fanout}")
        if not 1 <= self.max_reference_workers <= 16: raise ValueError("max_reference_workers must be 1..16")
        if self.reference_max_tokens <= 0 or self.max_total_model_calls <= 0 or self.max_total_output_tokens <= 0 or self.max_reference_profiles <= 0: raise ValueError("budgets must be positive")
        if self.privacy_mode not in {"display", "full"}: raise ValueError("privacy_mode must be display or full")

def _now() -> str: return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fanout_due(fanout: str, iteration: int) -> bool:
    if iteration == 0 or fanout == "user_turn": return iteration == 0
    if fanout == "per_iteration": return True
    if fanout.startswith("every_n:"): return iteration % int(fanout.split(":", 1)[1]) == 0
    raise ValueError(f"invalid fanout: {fanout}")

@dataclass
class ReferenceResult:
    profile: str
    persona_digest: str | None
    output: str = ""
    status: str = "passed"
    error: str | None = None
    output_tokens: int = 0
    wall_time_seconds: float = 0.0

@dataclass
class MoARunResult:
    run_id: str
    aggregator_profile: str
    reference_profiles: list[str]
    status: str
    aggregator_prompt: str = ""
    references: list[ReferenceResult] = field(default_factory=list)
    aggregator_response: str = ""
    error: str | None = None

ReferenceCaller = Callable[[ProfileContext, str, MoAOptions], ReferenceResult]
AggregatorCaller = Callable[[str, str, MoAOptions], tuple[str, str]]

def run_profile_aware_moa(task: str, aggregator_profile: str, reference_profiles: list[str], options: MoAOptions | None = None,
                          *, context: str = "", reference_caller: ReferenceCaller | None = None,
                          aggregator_caller: AggregatorCaller | None = None, run_id: str = "") -> MoARunResult:
    options = options or MoAOptions(); options.validate()
    if not aggregator_profile: raise ValueError("aggregator_profile is required")
    if aggregator_profile in reference_profiles: raise ValueError("aggregator cannot also be a reference")
    if len(reference_profiles) > options.max_reference_profiles:
        raise ValueError(f"reference profile budget exceeded: {len(reference_profiles)} > {options.max_reference_profiles}")
    agg = load_profile_context(aggregator_profile)
    refs = [load_profile_context(name) for name in reference_profiles]
    fingerprints = {}
    for profile in [agg, *refs]:
        if profile.configuration_fingerprint in fingerprints:
            raise ValueError(f"exact duplicate profile configuration: {profile.name} == {fingerprints[profile.configuration_fingerprint]}")
        fingerprints[profile.configuration_fingerprint] = profile.name
    result = MoARunResult(run_id=run_id or f"moa_{agg.name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}", aggregator_profile=agg.name, reference_profiles=reference_profiles, status="aggregator_started")
    def default_ref(profile: ProfileContext, prompt: str, opts: MoAOptions) -> ReferenceResult:
        return ReferenceResult(profile=profile.name, persona_digest=profile.persona_digest, status="blocked", error="no reference caller configured")
    caller = reference_caller or call_reference
    with ThreadPoolExecutor(max_workers=min(options.max_reference_workers, max(1, len(refs)))) as pool:
        futures = {pool.submit(caller, p, reference_prompt(p, task, context), options): p for p in refs}
        for future in as_completed(futures):
            profile = futures[future]
            try: result.references.append(future.result())
            except Exception as exc: result.references.append(ReferenceResult(profile=profile.name, persona_digest=profile.persona_digest, status="failed", error=str(exc)))
    result.references.sort(key=lambda item: item.profile)
    result.aggregator_prompt = aggregator_prompt(task, [{"profile": r.profile, "persona_digest": r.persona_digest, "output": r.output, "status": r.status} for r in result.references], context)
    if aggregator_caller is None:
        result.status = "blocked"; result.error = "no aggregator caller configured"; return result
    try:
        response, status = aggregator_caller(aggregator_profile, result.aggregator_prompt, options)
        result.aggregator_response, result.status = response, status
    except Exception as exc:
        result.status, result.error = "failed", str(exc)
    return result
