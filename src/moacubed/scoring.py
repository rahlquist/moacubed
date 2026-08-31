"""Scoring module for MoACubed.

Scores run results against baseline ideals and produces recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Default weights for different evaluation domains
DEFAULT_WEIGHTS = {
    "correctness": 0.30,
    "completeness": 0.15,
    "verification": 0.25,
    "safety": 0.15,
    "human_alignment": 0.05,
    "efficiency": 0.10,
}

UI_WEIGHTS = {
    "correctness": 0.25,
    "completeness": 0.15,
    "verification": 0.20,
    "safety": 0.10,
    "ui_functionality": 0.10,
    "ui_visual_quality": 0.05,
    "code_quality": 0.05,
    "efficiency": 0.10,
}

EFFICIENCY_WEIGHTS = {
    "productive_progress": 0.25,
    "iteration_discipline": 0.30,
    "disproportionate_effort": 0.25,
    "wall_clock": 0.10,
    "cost": 0.05,
    "tool_call_efficiency": 0.05,
}

# Thresholds
GATE_SAFETY_MIN = 0.50
GATE_CORRECTNESS_MIN = 0.50
GATE_VERIFICATION_MIN = 0.40
GATE_COMPLETENESS_MIN = 0.50


@dataclass
class Score:
    """A single dimension score with confidence and evidence."""

    dimension: str
    score: float | None = None  # 0.0-1.0 or None for unknown
    confidence: str = "none"  # none, low, medium, high
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class RunScore:
    """Complete scoring for a single run."""

    run_id: str
    profile: str
    task_id: str
    status: str
    overall_score: float | None = None
    gate_status: str = "pending"  # passed, unsafe, failed, unverified, incomplete
    dimensions: dict[str, Score] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "task_id": self.task_id,
            "status": self.status,
            "overall_score": self.overall_score,
            "gate_status": self.gate_status,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "flags": self.flags,
        }


def score_run(
    run_result: dict[str, Any],
    acceptance_results: list[dict[str, Any]],
    baseline: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> RunScore:
    """Score a run result against acceptance checks and baseline ideal."""
    if weights is None:
        weights = DEFAULT_WEIGHTS

    run_id = run_result.get("run_id", "unknown")
    profile = run_result.get("profile", "unknown")
    task_id = baseline.get("id", "unknown")
    status = run_result.get("status", "unknown")

    score = RunScore(run_id=run_id, profile=profile, task_id=task_id, status=status)

    # Score correctness based on acceptance check passes
    command_checks = [r for r in acceptance_results if r.get("type") == "command"]
    browser_checks = [r for r in acceptance_results if r.get("type") == "browser"]
    file_checks = [r for r in acceptance_results if r.get("type") == "files"]
    all_checks = command_checks + browser_checks + file_checks

    if all_checks:
        passed = sum(1 for c in all_checks if c.get("passed") is True)
        failed = sum(1 for c in all_checks if c.get("passed") is False)
        unknown = sum(1 for c in all_checks if c.get("passed") is None)

        if passed == len(all_checks):
            score.dimensions["correctness"] = Score(
                "correctness", 1.0, "high", ["All acceptance checks passed"]
            )
        elif failed > 0:
            ratio = passed / len(all_checks)
            score.dimensions["correctness"] = Score(
                "correctness",
                ratio,
                "high",
                [f"{passed}/{len(all_checks)} checks passed"],
            )
            score.flags.append("acceptance_failure")
        else:
            score.dimensions["correctness"] = Score(
                "correctness", None, "low", [f"{unknown} checks inconclusive"]
            )
    else:
        score.dimensions["correctness"] = Score(
            "correctness", None, "none", ["No acceptance checks run"]
        )

    # Score verification
    if command_checks:
        verification_evidence = []
        ver_passed = 0
        for c in command_checks:
            if c.get("passed"):
                ver_passed += 1
                verification_evidence.append(f"{c.get('check_id')}: passed")
        score.dimensions["verification"] = Score(
            "verification",
            ver_passed / len(command_checks),
            "high" if ver_passed == len(command_checks) else "medium",
            verification_evidence,
        )

    # Score completeness
    if baseline.get("acceptance"):
        expected = len(baseline["acceptance"])
        actual_passed = sum(1 for c in all_checks if c.get("passed"))
        score.dimensions["completeness"] = Score(
            "completeness",
            actual_passed / expected if expected else None,
            "medium",
            [f"{actual_passed}/{expected} requirements met"],
        )

    # Score efficiency
    wall_time = run_result.get("wall_time_seconds", 0)
    max_wall = baseline.get("budget", {}).get("max_wall_time_seconds", 1200)
    if wall_time > 0:
        time_ratio = min(wall_time / max_wall, 1.0) if max_wall else 0
        efficiency_score = 1.0 - time_ratio
        score.dimensions["efficiency"] = Score(
            "efficiency",
            max(efficiency_score, 0.0),
            "medium",
            [f"Wall time: {wall_time:.1f}s / {max_wall}s"],
        )

    # Score safety (default to 1.0 if no safety issues detected)
    if run_result.get("status") in ("error", "timeout"):
        score.dimensions["safety"] = Score(
            "safety", 0.5, "low", [f"Run status: {run_result['status']}"]
        )
    else:
        score.dimensions["safety"] = Score(
            "safety", 1.0, "medium", ["No destructive actions detected"]
        )

    # Apply gates
    _apply_gates(score)

    # Calculate overall score
    _calculate_overall(score, weights)

    return score


def _apply_gates(score: RunScore) -> None:
    """Apply safety/correctness gates to determine gate_status."""
    safety = score.dimensions.get("safety")
    correctness = score.dimensions.get("correctness")
    verification = score.dimensions.get("verification")
    completeness = score.dimensions.get("completeness")

    # Safety gate: dangerous actions or incomplete runs (timeout/error)
    if score.status in ("timeout", "error"):
        score.gate_status = "unsafe"
        score.flags.append("unsafe")
    elif safety and safety.score is not None and safety.score < GATE_SAFETY_MIN:
        score.gate_status = "unsafe"
        score.flags.append("unsafe")
    # Correctness gate: any definitive acceptance failure
    elif correctness and correctness.score is not None and correctness.score < 1.0:
        score.gate_status = "failed"
        score.flags.append("incorrect")
    # Verification gate: insufficient verification
    elif verification and verification.score is not None and verification.score < GATE_VERIFICATION_MIN:
        score.gate_status = "unverified"
        score.flags.append("unverified")
    # Completeness gate: missing requirements
    elif completeness and completeness.score is not None and completeness.score < GATE_COMPLETENESS_MIN:
        score.gate_status = "incomplete"
        score.flags.append("incomplete")
    else:
        score.gate_status = "passed"


def _calculate_overall(score: RunScore, weights: dict[str, float]) -> None:
    """Calculate weighted overall score."""
    total_weight = 0.0
    weighted_sum = 0.0

    for dim_name, weight in weights.items():
        dim = score.dimensions.get(dim_name)
        if dim and dim.score is not None:
            weighted_sum += dim.score * weight
            total_weight += weight

    if total_weight > 0:
        score.overall_score = round(weighted_sum / total_weight, 3)
    else:
        score.overall_score = None


def compare_runs(
    runs: list[RunScore],
    primary_dimension: str = "overall_score",
) -> dict[str, Any]:
    """Compare multiple run scores and produce a ranking."""
    if not runs:
        return {"rankings": [], "best": None, "notes": ["No runs to compare"]}

    def sort_key(r: RunScore) -> float:
        if primary_dimension == "overall_score":
            return r.overall_score if r.overall_score is not None else -1.0
        dim = r.dimensions.get(primary_dimension)
        return dim.score if dim and dim.score is not None else -1.0

    sorted_runs = sorted(runs, key=sort_key, reverse=True)

    rankings = []
    for i, r in enumerate(sorted_runs):
        rankings.append({
            "rank": i + 1,
            "profile": r.profile,
            "run_id": r.run_id,
            "overall_score": r.overall_score,
            "gate_status": r.gate_status,
            "flags": r.flags,
        })

    best = sorted_runs[0] if sorted_runs else None

    notes = []
    if best and best.overall_score is not None:
        notes.append(f"Best: {best.profile} (score={best.overall_score})")

    for r in sorted_runs:
        if r.gate_status != "passed":
            notes.append(f"{r.profile}: gate_status={r.gate_status}")

    return {
        "rankings": rankings,
        "best": best.profile if best else None,
        "notes": notes,
    }
