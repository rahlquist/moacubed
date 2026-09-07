from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from moacubed.trace_records import build_context_metadata, read_derived_index, write_aggregator_record, write_derived_index, write_profile_baseline


def test_aggregator_owned_record_and_context(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    monkeypatch.setenv("HERMES_HOME", str(home))
    record = {"run_id": "r1", "task_id": "t1", "context": build_context_metadata(
        {"profile": "default", "model": "agg"}, [{"profile": "research", "persona_only": True}], {"fanout": "user_turn"}
    ), "status": "passed", "overall_score": 0.9}
    path = write_aggregator_record("default", record)
    assert path == home / "moacubed-data" / "profile-moa.jsonl"
    saved = json.loads(path.read_text().strip())
    assert saved["storage"]["owner_role"] == "aggregator"
    assert saved["storage"]["owner_profile"] == "default"
    assert saved["context"]["references"][0]["persona_only"] is True


def test_profile_baseline_has_profile_owner(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    path = write_profile_baseline("research", {"run_id": "r2", "status": "passed"})
    assert path.name == "levelsets.jsonl"
    assert json.loads(path.read_text())["storage"]["owner_profile"] == "research"


def test_derived_index_is_compact(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    record = {"run_id": "r3", "task_id": "t3", "status": "passed", "overall_score": 0.8,
              "configuration_group": "g", "context": {"aggregator": {"profile": "default"},
              "references": [{"profile": "research"}]}, "aggregator_response": "secret raw output"}
    path = write_derived_index(record)
    assert "secret raw output" not in path.read_text()
    assert read_derived_index()[0]["aggregator_profile"] == "default"
