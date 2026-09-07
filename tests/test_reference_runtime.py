from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from moacubed.profile_context import ProfileContext
from moacubed.profile_moa import MoAOptions
import moacubed.reference_runtime as runtime


def test_call_reference_uses_hermes_bridge(monkeypatch):
    profile = ProfileContext("research", Path("/tmp"), "soul", "persona", "Be evidence based.", model="test-model", provider="test-provider")
    captured = {}
    class Proc:
        returncode = 0
        stdout = json.dumps({"status": "passed", "output": "advice", "output_tokens": 12})
        stderr = ""
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["payload"] = json.loads(kwargs["input"])
        return Proc()
    monkeypatch.setattr(runtime, "_hermes_python", lambda: "/usr/bin/python3")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    result = runtime.call_reference(profile, "task", MoAOptions())
    assert result.status == "passed"
    assert result.output == "advice"
    assert captured["payload"]["profile"]["model"] == "test-model"
    assert captured["payload"]["prompt"] == "task"


def test_call_reference_failure_is_recorded(monkeypatch):
    profile = ProfileContext("research", Path("/tmp"), "soul", "persona", "Be evidence based.")
    class Proc:
        returncode = 1
        stdout = ""
        stderr = "provider failure"
    monkeypatch.setattr(runtime, "_hermes_python", lambda: "/usr/bin/python3")
    monkeypatch.setattr(runtime.subprocess, "run", lambda *args, **kwargs: Proc())
    result = runtime.call_reference(profile, "task", MoAOptions())
    assert result.status == "failed"
    assert result.error == "provider failure"
