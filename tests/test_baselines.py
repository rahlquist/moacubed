"""End-to-end test: baseline loading, workspace materialization, and acceptance checks."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moacubed.baselines import (  # noqa: E402
    load_baseline,
    list_baselines,
    materialize_workspace,
    run_acceptance_checks,
)


def test_list_baselines():
    """Baselines are discoverable."""
    baselines = list_baselines()
    assert "ui-code-standard-v1" in baselines


def test_load_baseline():
    """Baseline loads with correct structure."""
    baseline = load_baseline("ui-code-standard-v1")
    assert baseline.id == "ui-code-standard"
    assert baseline.version == "v1"
    assert baseline.max_profiles == 8
    assert baseline.max_wall_time_seconds == 1200
    assert len(baseline.acceptance) >= 2


def test_materialize_workspace(tmp_path):
    """Workspace materialization creates isolated copy."""
    baseline = load_baseline("ui-code-standard-v1")
    workspace = materialize_workspace(baseline.fixture_dir, "test-profile")
    try:
        assert workspace.exists()
        assert (workspace / "index.html").exists()
        assert (workspace / "app.js").exists()
        assert (workspace / "style.css").exists()
        assert workspace != baseline.fixture_dir
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_acceptance_checks_fail_on_buggy_fixture():
    """Acceptance checks correctly fail against the buggy fixture."""
    baseline = load_baseline("ui-code-standard-v1")
    workspace = materialize_workspace(baseline.fixture_dir, "test-profile")
    try:
        results = run_acceptance_checks(baseline, workspace)
        failures = [r for r in results if r.get("passed") is False]
        assert len(failures) >= 1, "Expected at least one failure on buggy fixture"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_acceptance_checks_pass_on_fixed_fixture():
    """Acceptance checks pass after fixing the bug and adding visual distinction."""
    baseline = load_baseline("ui-code-standard-v1")
    workspace = materialize_workspace(baseline.fixture_dir, "test-profile")
    try:
        # Fix app.js
        fixed_js = """(function () {
    const STORAGE_KEY = 'counter:value';
    const countEl = document.getElementById('count');
    const incrementBtn = document.getElementById('increment');
    let count = parseInt(localStorage.getItem(STORAGE_KEY), 10) || 0;
    function render() { countEl.textContent = String(count); }
    incrementBtn.addEventListener('click', function () {
        count = count + 1;
        localStorage.setItem(STORAGE_KEY, String(count));
        render();
    });
    render();
})();
"""
        (workspace / "app.js").write_text(fixed_js)

        # Fix style.css
        fixed_css = (workspace / "style.css").read_text()
        fixed_css = fixed_css.replace("background: transparent;", "background: #fef3c7;")
        fixed_css = fixed_css.replace("border: 2px solid transparent;", "border: 2px solid #f59e0b;")
        fixed_css = fixed_css.replace("color: var(--fg);", "color: #92400e;")
        (workspace / "style.css").write_text(fixed_css)

        results = run_acceptance_checks(baseline, workspace)
        command_results = [r for r in results if r.get("type") == "command"]
        assert len(command_results) >= 1
        for r in command_results:
            assert r["passed"] is True, f"Check {r['check_id']} failed: {r}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
