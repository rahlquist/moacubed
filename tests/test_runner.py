"""Tests for the MoACubed runner module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moacubed.runner import (  # noqa: E402
    RunResult,
    _generate_run_id,
    _now,
    run_profile,
)


def test_generate_run_id():
    """Run ID is unique and contains profile name."""
    rid = _generate_run_id("test-profile", "task-v1")
    assert "test_profile" in rid
    assert "task-v1" in rid
    assert rid.startswith("run_")


def test_now_returns_iso_timestamp():
    """_now() returns RFC3339 UTC timestamp."""
    ts = _now()
    assert "T" in ts
    assert ts.endswith("Z")


def test_run_profile_hermes_not_found(tmp_path):
    """RunResult has error status when hermes is not usable."""
    result = run_profile(
        profile="nonexistent-profile-xyz",
        task_prompt="test prompt",
        workspace=tmp_path,
        budget={"max_wall_time_seconds": 10, "max_agent_iterations": 5},
    )
    assert result.status in ("blocked", "error", "failed")
    assert result.profile == "nonexistent-profile-xyz"


def test_run_result_dataclass():
    """RunResult can be created with required fields."""
    result = RunResult(
        run_id="test_001",
        profile="test",
        task_id="task",
        workspace=Path("/tmp"),
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
        status="passed",
    )
    assert result.status == "passed"
    assert result.profile == "test"
    assert result.model_calls == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
