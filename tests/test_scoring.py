"""Tests for the MoACubed scoring module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moacubed.scoring import (  # noqa: E402
    DEFAULT_WEIGHTS,
    GATE_CORRECTNESS_MIN,
    GATE_SAFETY_MIN,
    Score,
    RunScore,
    compare_runs,
    score_run,
)


def test_score_to_dict():
    """Score serializes to dict."""
    s = Score("correctness", 0.9, "high", ["All checks passed"])
    d = s.to_dict()
    assert d["score"] == 0.9
    assert d["confidence"] == "high"


def test_score_unknown():
    """Score with None is unknown."""
    s = Score("correctness")
    assert s.score is None
    assert s.confidence == "none"


def test_run_score_to_dict():
    """RunScore serializes to dict."""
    rs = RunScore(run_id="r1", profile="p1", task_id="t1", status="passed")
    d = rs.to_dict()
    assert d["run_id"] == "r1"
    assert d["profile"] == "p1"


def test_score_run_all_pass():
    """Perfect acceptance results yield high scores."""
    run_result = {
        "run_id": "r1",
        "profile": "p1",
        "status": "passed",
        "wall_time_seconds": 10.0,
    }
    acceptance = [
        {"type": "command", "check_id": "tests", "passed": True},
        {"type": "command", "check_id": "build", "passed": True},
    ]
    baseline = {
        "id": "t1",
        "acceptance": [{"id": "tests"}, {"id": "build"}],
        "budget": {"max_wall_time_seconds": 1200},
    }

    score = score_run(run_result, acceptance, baseline)
    assert score.gate_status == "passed"
    assert score.overall_score is not None
    assert score.overall_score > 0.8


def test_score_run_with_failure():
    """Failed acceptance results yield lower scores and gate failure."""
    run_result = {
        "run_id": "r1",
        "profile": "p1",
        "status": "failed",
        "wall_time_seconds": 10.0,
    }
    acceptance = [
        {"type": "command", "check_id": "tests", "passed": False},
        {"type": "command", "check_id": "build", "passed": True},
    ]
    baseline = {
        "id": "t1",
        "acceptance": [{"id": "tests"}, {"id": "build"}],
        "budget": {"max_wall_time_seconds": 1200},
    }

    score = score_run(run_result, acceptance, baseline)
    assert score.gate_status == "failed"
    assert "acceptance_failure" in score.flags


def test_score_run_timeout():
    """Timeout results in safety concern."""
    run_result = {
        "run_id": "r1",
        "profile": "p1",
        "status": "timeout",
        "wall_time_seconds": 1200.0,
    }
    acceptance = []
    baseline = {
        "id": "t1",
        "acceptance": [],
        "budget": {"max_wall_time_seconds": 1200},
    }

    score = score_run(run_result, acceptance, baseline)
    assert score.gate_status == "unsafe"


def test_score_run_no_checks():
    """No acceptance checks yields unknown correctness."""
    run_result = {
        "run_id": "r1",
        "profile": "p1",
        "status": "passed",
        "wall_time_seconds": 5.0,
    }
    acceptance = []
    baseline = {"id": "t1", "acceptance": [], "budget": {}}

    score = score_run(run_result, acceptance, baseline)
    assert score.dimensions["correctness"].score is None


def test_compare_runs_basic():
    """compare_runs ranks runs correctly."""
    runs = [
        RunScore("r1", "p1", "t1", "passed", overall_score=0.9),
        RunScore("r2", "p2", "t1", "passed", overall_score=0.7),
        RunScore("r3", "p3", "t1", "passed", overall_score=0.8),
    ]
    result = compare_runs(runs)
    assert result["best"] == "p1"
    assert result["rankings"][0]["profile"] == "p1"
    assert result["rankings"][-1]["profile"] == "p2"


def test_compare_runs_empty():
    """compare_runs handles empty list."""
    result = compare_runs([])
    assert result["best"] is None
    assert result["rankings"] == []


def test_compare_runs_with_none():
    """compare_runs treats None scores as worst."""
    runs = [
        RunScore("r1", "p1", "t1", "passed", overall_score=None),
        RunScore("r2", "p2", "t1", "passed", overall_score=0.5),
    ]
    result = compare_runs(runs)
    assert result["best"] == "p2"


def test_default_weights_sum():
    """Default weights should be reasonable (not required to sum to 1)."""
    total = sum(DEFAULT_WEIGHTS.values())
    assert 0.9 < total <= 1.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
