"""Hermes profile runner for MoACubed.

Executes a single profile against a task in an isolated workspace and captures
the result for scoring.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RunResult:
    """Result of running a profile against a task."""

    run_id: str
    profile: str
    task_id: str
    workspace: Path
    started_at: str
    finished_at: str
    status: str  # passed | partial | failed | timeout | blocked | error
    stdout: str = ""
    stderr: str = ""
    final_response: str = ""
    files_changed: list[str] = field(default_factory=list)
    model_calls: int = 0
    tool_calls: int = 0
    agent_iterations: int = 0
    productive_iterations: int = 0
    unproductive_iterations: int = 0
    tokens_used: int = 0
    wall_time_seconds: float = 0.0
    error: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_run_id(profile: str, task_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_profile = profile.replace("-", "_")
    return f"run_{safe_profile}_{task_id}_{ts}"


def run_profile(
    profile: str,
    task_prompt: str,
    workspace: Path,
    budget: dict[str, Any],
    *,
    model: str | None = None,
    provider: str | None = None,
    moa_preset: str | None = None,
) -> RunResult:
    """Run a single profile against a task in an isolated workspace.

    Uses `hermes chat -q` for one-shot execution. The profile is selected via
    `--profile`. The workspace becomes the working directory.

    Returns a RunResult with captured output and status.
    """
    run_id = _generate_run_id(profile, "task")
    started_at = _now()
    start_time = time.monotonic()

    max_turns = int(budget.get("max_agent_iterations", 20))
    max_wall = int(budget.get("max_wall_time_seconds", 1200))

    # Build the hermes command
    cmd = ["hermes", "chat", "-q", task_prompt, "--profile", profile]

    if model:
        cmd.extend(["-m", model])
    if provider:
        cmd.extend(["--provider", provider])
    if moa_preset:
        cmd.extend(["--moa-preset", moa_preset])

    cmd.extend(["--max-turns", str(max_turns)])

    # Snapshot files before
    files_before = set()
    if workspace.exists():
        for p in workspace.rglob("*"):
            if p.is_file():
                files_before.add(str(p.relative_to(workspace)))

    try:
        result = subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=max_wall,
            env={**os.environ, "MOACUBED_RUN_ID": run_id},
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
        error = None

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        exit_code = -1
        error = f"timeout after {max_wall}s"
    except FileNotFoundError:
        stdout = ""
        stderr = ""
        exit_code = -2
        error = "hermes command not found on PATH"
    except Exception as e:
        stdout = ""
        stderr = str(e)
        exit_code = -3
        error = str(e)

    finished_at = _now()
    wall_time = time.monotonic() - start_time

    # Detect changed files
    files_after = set()
    if workspace.exists():
        for p in workspace.rglob("*"):
            if p.is_file():
                files_after.add(str(p.relative_to(workspace)))

    files_changed = sorted(files_after - files_before)

    # Determine status
    if error:
        if "timeout" in error:
            status = "timeout"
        elif "not found" in error:
            status = "blocked"
        else:
            status = "error"
    elif exit_code == 0:
        status = "passed"
    else:
        status = "failed"

    return RunResult(
        run_id=run_id,
        profile=profile,
        task_id="task",
        workspace=workspace,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        stdout=stdout[-10000:] if stdout else "",
        stderr=stderr[-5000:] if stderr else "",
        final_response=stdout.strip() if stdout else "",
        files_changed=files_changed,
        wall_time_seconds=round(wall_time, 2),
        error=error,
    )


def run_browser_check(
    check: dict[str, Any],
    workspace: Path,
    *,
    headless: bool = True,
) -> dict[str, Any]:
    """Run a browser-based acceptance check using Playwright."""
    check_id = check.get("id", "unknown")
    description = check.get("description", "")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "check_id": check_id,
            "type": "browser",
            "passed": None,
            "error": "playwright not installed",
        }

    url = check.get("url", "")
    if not url:
        # Try to find index.html in workspace
        index = workspace / "index.html"
        if index.exists():
            url = index.as_uri()
        else:
            return {
                "check_id": check_id,
                "type": "browser",
                "passed": None,
                "error": "no URL or index.html found",
            }

    assertions = check.get("assertions", [])

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url)

            results = []
            all_passed = True

            for assertion in assertions:
                selector = assertion.get("selector", "")
                prop = assertion.get("property", "")
                condition = assertion.get("condition", "equals")
                expected = assertion.get("value", "")

                try:
                    if prop:
                        actual = page.evaluate(
                            "(el, prop) => getComputedStyle(el)[prop]",
                            page.query_selector(selector),
                            prop,
                        )
                    else:
                        actual = page.inner_text(selector)

                    if condition == "equals":
                        passed = str(actual) == str(expected)
                    elif condition == "not_equals":
                        passed = str(actual) != str(expected)
                    elif condition == "contains":
                        passed = str(expected) in str(actual)
                    elif condition == "not_contains":
                        passed = str(expected) not in str(actual)
                    else:
                        passed = False

                    results.append({
                        "selector": selector,
                        "property": prop,
                        "expected": expected,
                        "actual": actual,
                        "passed": passed,
                    })
                    if not passed:
                        all_passed = False
                except Exception as e:
                    results.append({
                        "selector": selector,
                        "error": str(e),
                        "passed": False,
                    })
                    all_passed = False

            browser.close()
            return {
                "check_id": check_id,
                "type": "browser",
                "passed": all_passed,
                "results": results,
                "description": description,
            }
    except Exception as e:
        return {
            "check_id": check_id,
            "type": "browser",
            "passed": None,
            "error": str(e),
        }
