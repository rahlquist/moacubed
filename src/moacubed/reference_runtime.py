"""Real Hermes auxiliary-client adapter for persona-only references."""
from __future__ import annotations
import glob
import importlib
import json
import os
import subprocess
import shutil
import sys
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING
from .profile_context import ProfileContext
if TYPE_CHECKING:
    from .profile_moa import MoAOptions, ReferenceResult


def _result(**kwargs):
    from .profile_moa import ReferenceResult
    return ReferenceResult(**kwargs)


def _text(response: Any) -> str:
    if isinstance(response, str):
        return response
    for attr in ("output_text", "content", "text"):
        value = getattr(response, attr, None)
        if isinstance(value, str):
            return value
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    return str(response) if response is not None else ""


def _usage_tokens(response: Any) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    total = getattr(usage, "total_tokens", None)
    if total is not None:
        return int(total)
    return int(getattr(usage, "completion_tokens", 0) or 0) + int(getattr(usage, "prompt_tokens", 0) or 0)


def _ensure_hermes_import_path() -> None:
    """Make installed Hermes source and its venv packages importable."""
    candidates: list[Path] = []
    executable = shutil.which("hermes")
    if executable:
        path = Path(executable).resolve()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines:
            if 'exec "' not in line:
                continue
            target = Path(line.split('exec "', 1)[1].split('"', 1)[0]).resolve()
            candidates.extend([target.parent.parent, target.parent.parent.parent])
            for site in glob.glob(str(target.parent.parent / "lib" / "python*" / "site-packages")):
                if site not in sys.path:
                    sys.path.insert(0, site)
    configured = os.environ.get("HERMES_AGENT_HOME")
    if configured:
        candidates.append(Path(configured).expanduser())
    for candidate in candidates:
        if (candidate / "agent").is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
            return


def _runtime(profile: ProfileContext) -> dict[str, Any]:
    """Resolve provider runtime without persisting credentials."""
    try:
        _ensure_hermes_import_path()
        resolver = importlib.import_module("hermes_cli.runtime_provider")
        return resolver.resolve_runtime_provider(requested=profile.provider, target_model=profile.model)
    except Exception:
        return {"provider": profile.provider, "model": profile.model}


def _hermes_python() -> str | None:
    executable = shutil.which("hermes")
    if not executable:
        return None
    try:
        for line in Path(executable).resolve().read_text(encoding="utf-8").splitlines():
            if 'exec "' in line:
                target = Path(line.split('exec "', 1)[1].split('"', 1)[0]).resolve()
                candidate_python = target.parent / "python"
                return str(candidate_python if candidate_python.exists() else target)
    except OSError:
        return None
    return None


def call_reference(profile: ProfileContext, prompt: str, options: MoAOptions) -> ReferenceResult:
    """Call Hermes' auxiliary client in Hermes' own Python environment."""
    started = time.monotonic()
    bridge = Path(__file__).with_name("reference_bridge.py")
    payload = {"profile": profile.short_identity, "prompt": prompt,
               "max_tokens": options.reference_max_tokens, "timeout": options.reference_timeout_seconds}
    try:
        python = _hermes_python()
        if not python:
            return _result(profile=profile.name, persona_digest=profile.persona_digest, status="blocked", error="hermes executable not found")
        proc = subprocess.run([python, str(bridge)], input=json.dumps(payload), text=True,
                              capture_output=True, timeout=options.reference_timeout_seconds + 15,
                              env={**os.environ, "PYTHONPATH": ""})
        if proc.returncode != 0:
            return _result(profile=profile.name, persona_digest=profile.persona_digest, status="failed",
                           error=(proc.stderr or proc.stdout)[-2000:], wall_time_seconds=round(time.monotonic() - started, 3))
        data = json.loads(proc.stdout.strip().splitlines()[-1])
        return _result(profile=profile.name, persona_digest=profile.persona_digest,
                       output=data.get("output", ""), status=data.get("status", "passed"),
                       output_tokens=int(data.get("output_tokens", 0)), wall_time_seconds=round(time.monotonic() - started, 3))
    except subprocess.TimeoutExpired:
        return _result(profile=profile.name, persona_digest=profile.persona_digest, status="timeout",
                       error="reference bridge timeout", wall_time_seconds=round(time.monotonic() - started, 3))
    except Exception as exc:
        return _result(profile=profile.name, persona_digest=profile.persona_digest, status="failed",
                       error=str(exc), wall_time_seconds=round(time.monotonic() - started, 3))
