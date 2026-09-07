"""Native versus profile-aware MoA comparison records."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ComparisonResult:
    mode: str
    status: str
    score: float | None
    verification: float | None
    wall_time_seconds: float | None
    model_calls: int | None
    notes: tuple[str, ...] = ()


def compare_modes(results: list[ComparisonResult]) -> dict[str, Any]:
    """Rank verified mode results without treating unknown as failure."""
    ranked = sorted(results, key=lambda item: item.score if item.score is not None else -1.0, reverse=True)
    return {
        "rankings": [
            {"rank": idx + 1, "mode": item.mode, "status": item.status, "score": item.score,
             "verification": item.verification, "wall_time_seconds": item.wall_time_seconds,
             "model_calls": item.model_calls, "notes": list(item.notes)}
            for idx, item in enumerate(ranked)
        ],
        "best": ranked[0].mode if ranked and ranked[0].score is not None else None,
        "confidence": "low" if len(results) < 3 else "medium",
    }


def comparison_record(task_id: str, results: list[ComparisonResult]) -> dict[str, Any]:
    return {"schema_version": 1, "task_id": task_id, "modes": compare_modes(results)}
