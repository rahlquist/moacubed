"""Append-only profile-aware MoA trace records."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .foundation import moacubed_dir

def write_profile_moa_trace(profile: str, record: dict[str, Any]) -> Path:
    directory = moacubed_dir(profile); directory.mkdir(parents=True, exist_ok=True)
    path = directory / "profile-moa.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path

def read_profile_moa_traces(profile: str) -> list[dict[str, Any]]:
    path = moacubed_dir(profile) / "profile-moa.jsonl"
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
