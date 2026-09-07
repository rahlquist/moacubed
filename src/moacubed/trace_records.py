"""Append-only profile-aware MoA trace records."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .foundation import moacubed_dir

def write_profile_moa_trace(profile: str, record: dict[str, Any]) -> Path:
    """Append a MoA run under the aggregator's profile ledger."""
    record.setdefault("schema_version", 1)
    record.setdefault("storage", {})
    record["storage"].setdefault("owner_role", "aggregator")
    record["storage"].setdefault("owner_profile", profile)
    directory = moacubed_dir(profile)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "profile-moa.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path


def write_aggregator_record(profile: str, record: dict[str, Any]) -> Path:
    """Explicit alias documenting aggregator-owned result storage."""
    return write_profile_moa_trace(profile, record)


def write_profile_baseline(profile: str, record: dict[str, Any]) -> Path:
    """Store standalone acting-profile level-set evidence with that profile."""
    record.setdefault("schema_version", 1)
    record.setdefault("storage", {})
    record["storage"].setdefault("owner_role", "profile")
    record["storage"].setdefault("owner_profile", profile)
    directory = moacubed_dir(profile)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "levelsets.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path


def build_context_metadata(aggregator: dict[str, Any], references: list[dict[str, Any]], moa: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build explicit aggregator/reference role metadata for every run."""
    return {
        "aggregator": aggregator,
        "references": references,
        "moa": moa or {},
    }


def aggregate_index_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a compact cross-context record without duplicating raw output."""
    context = record.get("context", {})
    return {
        "run_id": record.get("run_id"),
        "task_id": record.get("task_id"),
        "aggregator_profile": context.get("aggregator", {}).get("profile"),
        "reference_profiles": [r.get("profile") for r in context.get("references", [])],
        "status": record.get("status"),
        "overall_score": record.get("overall_score"),
        "configuration_group": record.get("configuration_group"),
    }


def write_derived_index(record: dict[str, Any]) -> Path:
    """Append a compact cross-aggregator index record under the Hermes home."""
    root = moacubed_dir(None).parent / "moacubed-index"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "profile-performance.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(aggregate_index_record(record), ensure_ascii=False, default=str) + "\n")
    return path


def read_derived_index() -> list[dict[str, Any]]:
    path = moacubed_dir(None).parent / "moacubed-index" / "profile-performance.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def read_profile_moa_traces(profile: str) -> list[dict[str, Any]]:
    path = moacubed_dir(profile) / "profile-moa.jsonl"
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
