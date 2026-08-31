"""Baseline task loading and execution for MoACubed."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@dataclass
class BaselineTask:
    """A versioned baseline task with acceptance checks and budget."""

    id: str
    version: str
    title: str
    prompt: str
    fixture_dir: Path
    acceptance: list[dict[str, Any]]
    ideal: dict[str, Any]
    effort_expectations: dict[str, Any]
    budget: dict[str, Any]

    @property
    def max_profiles(self) -> int:
        return int(self.budget.get("max_profiles", 8))

    @property
    def max_wall_time_seconds(self) -> int:
        return int(self.budget.get("max_wall_time_seconds", 1200))


def load_baseline(name: str) -> BaselineTask:
    """Load a baseline task by name (e.g. 'ui-code-standard-v1')."""
    # Resolve fixture directory
    fixture_dir = FIXTURES_DIR / name
    if not fixture_dir.exists():
        raise FileNotFoundError(f"Baseline fixture not found: {fixture_dir}")

    # Load task.yaml
    task_yaml = fixture_dir / "task.yaml"
    if not task_yaml.exists():
        raise FileNotFoundError(f"Baseline task.yaml not found: {task_yaml}")

    import yaml

    with task_yaml.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return BaselineTask(
        id=data.get("id", name),
        version=data.get("version", "v1"),
        title=data.get("title", name),
        prompt=data.get("prompt", ""),
        fixture_dir=fixture_dir,
        acceptance=data.get("acceptance", []),
        ideal=data.get("ideal", {}),
        effort_expectations=data.get("effort_expectations", {}),
        budget=data.get("budget", {}),
    )


def list_baselines() -> list[str]:
    """List all available baseline names."""
    if not FIXTURES_DIR.exists():
        return []
    return sorted(
        d.name for d in FIXTURES_DIR.iterdir() if d.is_dir() and (d / "task.yaml").exists()
    )


def materialize_workspace(fixture_dir: Path, profile: str) -> Path:
    """Create an isolated workspace for a profile run."""
    workspace_root = Path(tempfile.mkdtemp(prefix=f"moacubed-{profile}-"))
    # Copy fixture contents into the workspace (including .venv if present)
    for item in fixture_dir.iterdir():
        if item.is_dir():
            shutil.copytree(item, workspace_root / item.name)
        else:
            shutil.copy2(item, workspace_root / item.name)
    return workspace_root


def run_command_check(check: dict[str, Any], cwd: Path) -> dict[str, Any]:
    """Run a command-based acceptance check and return the result."""
    command = check.get("command", "")
    expected_exit = int(check.get("expected_exit_code", 0))

    # If command uses `python -m pytest`, try to find a working pytest
    if "python" in command and "pytest" in command:
        # Try to find a venv with pytest in the workspace or its parents
        for search_dir in [cwd, *cwd.parents]:
            venv_python = search_dir / ".venv" / "bin" / "python"
            if venv_python.exists():
                command = command.replace("python", str(venv_python), 1)
                break

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = result.returncode == expected_exit
        return {
            "check_id": check.get("id", "unknown"),
            "type": "command",
            "passed": passed,
            "expected_exit_code": expected_exit,
            "actual_exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "check_id": check.get("id", "unknown"),
            "type": "command",
            "passed": False,
            "error": "timeout",
        }
    except Exception as e:
        return {
            "check_id": check.get("id", "unknown"),
            "type": "command",
            "passed": False,
            "error": str(e),
        }


def run_file_check(check: dict[str, Any], cwd: Path) -> dict[str, Any]:
    """Run a file-based acceptance check."""
    # File checks verify expected files exist or don't exist
    assertions = check.get("assertions", [])
    results = []
    passed = True
    for assertion in assertions:
        expected_path = assertion.get("path", "")
        should_exist = assertion.get("exists", True)
        actual = (cwd / expected_path).exists()
        ok = actual == should_exist
        if not ok:
            passed = False
        results.append({"path": expected_path, "expected": should_exist, "actual": actual, "ok": ok})

    return {
        "check_id": check.get("id", "unknown"),
        "type": "files",
        "passed": passed,
        "results": results,
    }


def run_acceptance_checks(baseline: BaselineTask, workspace: Path) -> list[dict[str, Any]]:
    """Run all acceptance checks for a baseline in a workspace."""
    results = []
    for check in baseline.acceptance:
        check_type = check.get("type", "command")
        if check_type == "command":
            results.append(run_command_check(check, workspace))
        elif check_type == "files":
            results.append(run_file_check(check, workspace))
        elif check_type == "browser":
            # Browser checks require Playwright — mark as manual if not invoked via runner
            results.append({
                "check_id": check.get("id", "unknown"),
                "type": "browser",
                "passed": None,
                "note": "browser check requires Playwright runner",
            })
        else:
            results.append({
                "check_id": check.get("id", "unknown"),
                "type": check_type,
                "passed": None,
                "note": f"unknown check type: {check_type}",
            })
    return results
