"""Normal Hermes subprocess boundary for the MoACubed aggregator."""
from __future__ import annotations
import os, subprocess
from pathlib import Path
from typing import Any
from .profile_moa import MoAOptions

def run_aggregator_profile(profile: str, prompt: str, workspace: Path, options: MoAOptions, *, hermes_command: str = "hermes") -> tuple[str, str]:
    cmd = [hermes_command, "chat", "-q", prompt, "--profile", profile, "--max-turns", str(options.aggregator_max_turns), "--quiet"]
    try:
        proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True, timeout=options.aggregator_timeout_seconds,
                              env={**os.environ, "MOACUBED_MODE": options.native_compatibility_label})
    except subprocess.TimeoutExpired as exc:
        return ((exc.stdout or "") if isinstance(exc.stdout, str) else "", "timeout")
    except FileNotFoundError:
        return ("", "blocked")
    return (proc.stdout[-20000:], "passed" if proc.returncode == 0 else "failed")
