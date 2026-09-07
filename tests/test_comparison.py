from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from moacubed.comparison import ComparisonResult, compare_modes, comparison_record


def test_compare_modes_ranks_verified_scores():
    result = compare_modes([
        ComparisonResult("native_moa", "passed", 0.7, 1.0, 5, 3),
        ComparisonResult("profile_aware_full", "passed", 0.9, 1.0, 7, 4),
        ComparisonResult("uncertain", "blocked", None, None, None, None),
    ])
    assert result["best"] == "profile_aware_full"
    assert result["rankings"][0]["rank"] == 1
    assert result["rankings"][-1]["score"] is None


def test_comparison_record_has_schema():
    record = comparison_record("task-1", [ComparisonResult("native_moa", "passed", 0.5, 1.0, 1, 2)])
    assert record["schema_version"] == 1
    assert record["task_id"] == "task-1"
