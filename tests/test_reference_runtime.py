from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from moacubed.profile_context import ProfileContext
from moacubed.profile_moa import MoAOptions
import moacubed.reference_runtime as runtime


def test_call_reference_uses_tool_free_auxiliary_call(monkeypatch):
    profile = ProfileContext("research", Path("/tmp"), "soul", "persona", "Be evidence based.", model="test-model", provider="test-provider")
    captured = {}
    class Usage: total_tokens = 12
    class Response: content = "advice"; usage = Usage()
    class Aux:
        def call_llm(self, **kwargs):
            captured.update(kwargs)
            return Response()
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: Aux() if name == "agent.auxiliary_client" else None)
    monkeypatch.setattr(runtime, "_runtime", lambda profile: {})
    result = runtime.call_reference(profile, "task", MoAOptions())
    assert result.status == "passed"
    assert result.output == "advice"
    assert captured["task"] == "moa_reference"
    assert captured["tools"] is None
    assert captured["model"] == "test-model"


def test_call_reference_failure_is_recorded(monkeypatch):
    profile = ProfileContext("research", Path("/tmp"), "soul", "persona", "Be evidence based.")
    class Aux:
        def call_llm(self, **kwargs): raise TimeoutError("slow")
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: Aux())
    monkeypatch.setattr(runtime, "_runtime", lambda profile: {})
    result = runtime.call_reference(profile, "task", MoAOptions())
    assert result.status == "timeout"
    assert result.error == "slow"
