from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from moacubed.profile_context import load_profile_context, sanitize_persona
from moacubed.persona_prompt import reference_prompt, aggregator_prompt
from moacubed.profile_moa import MoAOptions, ReferenceResult, fanout_due, run_profile_aware_moa


def test_sanitize_persona_redacts_secrets():
    result = sanitize_persona("Use ghp_abcdefghijklmnopqrstuvwxyz and stay direct.")
    assert "ghp_" not in result
    assert "[redacted secret]" in result


def test_profile_context_temp_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"; profile = home / "profiles" / "security"
    profile.mkdir(parents=True)
    (profile / "SOUL.md").write_text("Be skeptical and verify claims.")
    monkeypatch.setenv("HERMES_HOME", str(home))
    ctx = load_profile_context("security")
    assert ctx.name == "security"
    assert "verify claims" in ctx.persona
    assert ctx.persona_digest


def test_prompts_have_role_boundaries():
    from moacubed.profile_context import ProfileContext
    p = ProfileContext("x", Path("/tmp"), "s", "p", "Be careful.")
    ref = reference_prompt(p, "Find the bug")
    assert "no tools" in ref.lower()
    assert "BEGIN REFERENCE PERSONA DATA" in ref
    agg = aggregator_prompt("Fix it", [{"profile": "x", "persona_digest": "p", "output": "Check timeout."}])
    assert "final decision-maker" in agg
    assert "Check timeout." in agg


def test_fanout_cadence():
    assert [fanout_due("user_turn", i) for i in range(3)] == [True, False, False]
    assert [fanout_due("per_iteration", i) for i in range(3)] == [True, True, True]
    assert [fanout_due("every_n:3", i) for i in range(7)] == [True, False, False, True, False, False, True]


def test_profile_aware_run_isolates_reference_failures(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    for name in ("agg", "a", "b"):
        path = home if name == "agg" else home / "profiles" / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "SOUL.md").write_text(f"Persona {name}")
    monkeypatch.setenv("HERMES_HOME", str(home))
    def ref(profile, prompt, options):
        if profile.name == "b": return ReferenceResult(profile.name, profile.persona_digest, status="failed", error="provider")
        return ReferenceResult(profile.name, profile.persona_digest, output="use tests")
    def agg(profile, prompt, options):
        assert "use tests" in prompt
        return "done", "passed"
    result = run_profile_aware_moa("Fix bug", "agg", ["a", "b"], reference_caller=ref, aggregator_caller=agg)
    assert result.status == "passed"
    assert len(result.references) == 2
    assert {r.status for r in result.references} == {"passed", "failed"}


def test_invalid_options_fail_before_calls():
    try:
        MoAOptions(fanout="every_n:1").validate()
    except ValueError:
        pass
    else:
        raise AssertionError("invalid fanout accepted")
