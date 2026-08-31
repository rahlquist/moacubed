"""MoACubed shared foundation.

Provides:
  - Profile discovery and configuration canonicalization
  - Configuration fingerprinting for duplicate detection
  - Distinctiveness preflight comparison
  - Budget accounting
  - Append-only JSONL record writer
  - Human-readable ledger generation/update
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def hermes_home() -> Path:
    """Resolve $HERMES_HOME, defaulting to ~/.hermes."""
    raw = os.environ.get("HERMES_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".hermes"


def profile_home(profile: str | None = None) -> Path:
    """Return the home directory for a profile (default profile if None)."""
    home = hermes_home()
    if profile and profile != "default":
        return home / "profiles" / profile
    return home


def moacubed_dir(profile: str | None = None) -> Path:
    """Return the moacubed-data directory for a profile."""
    return profile_home(profile) / "moacubed-data"


def ledger_path(profile: str | None = None) -> Path:
    """Return the path to the profile's moacubed.md ledger."""
    return profile_home(profile) / "moacubed.md"


# ---------------------------------------------------------------------------
# Schemas (record type discriminators)
# ---------------------------------------------------------------------------


REVIEW_SCHEMA_VERSION = 1
RUN_SCHEMA_VERSION = 1
RECOMMENDATION_SCHEMA_VERSION = 1
PREFLIGHT_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Canonicalization helpers
# ---------------------------------------------------------------------------


def _normalize_whitespace(text: str) -> str:
    """Collapse internal whitespace and strip surrounding whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def _canonicalize_string(value: Any) -> Any:
    """Recursively canonicalize strings inside a structure."""
    if isinstance(value, str):
        return _normalize_whitespace(value)
    if isinstance(value, list):
        return [_canonicalize_string(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonicalize_string(v) for k, v in value.items()}
    return value


def _digest(obj: Any) -> str:
    """Return a stable sha256 hex digest of a JSON-serialized object."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest_file(path: Path) -> str | None:
    """Return a sha256 hex digest of a file's contents, or None if unreadable."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Profile configuration fingerprint
# ---------------------------------------------------------------------------


@dataclass
class ProfileConfig:
    """A canonical representation of a Hermes profile's configuration."""

    profile: str | None
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    system_instruction_digest: str | None = None
    soul_digest: str | None = None
    soul_canonical: str | None = None
    moa: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """Return a stable configuration fingerprint."""
        return _digest(_canonicalize_dict(asdict(self)))


def _canonicalize_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize a dict for stable comparison.

    - Drops known ephemeral keys (timestamps, runtime paths).
    - Sorts lists.
    - Normalizes whitespace in strings.
    """
    drop_keys = {"created_at", "updated_at", "started_at", "finished_at", "run_id"}
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k in drop_keys:
            continue
        if isinstance(v, str):
            out[k] = _normalize_whitespace(v)
        elif isinstance(v, list):
            out[k] = sorted(
                (_normalize_whitespace(x) if isinstance(x, str) else x for x in v),
                key=str,
            )
        elif isinstance(v, dict):
            out[k] = _canonicalize_dict(v)
        else:
            out[k] = v
    return out


def discover_profiles() -> list[str]:
    """Return the list of known profile names (including 'default')."""
    home = hermes_home()
    profiles: list[str] = ["default"]
    profile_dir = home / "profiles"
    if profile_dir.is_dir():
        for child in sorted(profile_dir.iterdir()):
            if child.is_dir() and (child / "SOUL.md").exists():
                profiles.append(child.name)
    return profiles


def _read_soul_canonical(path: Path) -> tuple[str, str]:
    """Read a SOUL.md and return (digest, canonical_content).

    Canonicalization strips comments, collapses whitespace, and lowercases so
    cosmetic edits do not trigger false distinctiveness.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return ("", "")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("# "):
            # skip comment-only lines that aren't markdown headings
            pass
        else:
            lines.append(stripped)
    canonical = _normalize_whitespace("\n".join(lines)).lower()
    return digest, canonical


def load_profile_config(profile: str | None) -> ProfileConfig:
    """Load the canonical configuration for a profile."""
    home = profile_home(profile)
    soul = home / "SOUL.md"
    soul_digest, soul_canonical = _read_soul_canonical(soul) if soul.exists() else (None, None)

    # Detect skills
    skills_dir = home / "skills"
    skills: list[str] = []
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").exists():
                skills.append(child.name)

    return ProfileConfig(
        profile=profile or "default",
        soul_digest=soul_digest,
        soul_canonical=soul_canonical,
        skills=skills,
    )


# ---------------------------------------------------------------------------
# Distinctiveness preflight
# ---------------------------------------------------------------------------


@dataclass
class DistinctivenessResult:
    """Result of comparing a candidate profile against existing profiles."""

    candidate: str
    closest_profile: str | None = None
    similarity: float = 0.0
    status: str = "unknown"  # exact_duplicate | near_duplicate | irrelevant_difference | meaningful_difference
    differences: list[dict[str, str]] = field(default_factory=list)
    needs_confirmation: bool = False
    decision: str = "pending"  # pending | run | skip | cancel


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _soul_similarity(a: str | None, b: str | None) -> float:
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    # Token-based Jaccard on whitespace-separated words
    ta = set(a.split())
    tb = set(b.split())
    return _jaccard(ta, tb)


def _digest_similarity(digest_a: str | None, digest_b: str | None) -> float:
    """Compare two content digests directly."""
    if digest_a is None and digest_b is None:
        return 1.0
    if digest_a is None or digest_b is None:
        return 0.0
    return 1.0 if digest_a == digest_b else 0.0


def compare_profiles(candidate: ProfileConfig, others: list[ProfileConfig]) -> DistinctivenessResult:
    """Compare a candidate profile against others and classify distinctiveness."""
    if not others:
        return DistinctivenessResult(
            candidate=candidate.profile or "default",
            status="meaningful_difference",
            needs_confirmation=False,
            decision="run",
        )

    best: DistinctivenessResult | None = None
    for other in others:
        diffs: list[dict[str, str]] = []
        digest_equal = (
            candidate.soul_digest is not None
            and other.soul_digest is not None
            and candidate.soul_digest == other.soul_digest
        )

        if candidate.soul_digest and other.soul_digest:
            if not digest_equal:
                diffs.append({"path": "SOUL.md", "detail": "content differs"})
        elif candidate.soul_digest != other.soul_digest:
            diffs.append({"path": "SOUL.md", "detail": "presence differs"})

        skill_diff = set(candidate.skills) ^ set(other.skills)
        if skill_diff:
            diffs.append({"path": "skills", "detail": f"skills differ: {sorted(skill_diff)}"})

        # Use canonical content similarity when available; otherwise fall back to digest comparison.
        if candidate.soul_canonical is not None and other.soul_canonical is not None:
            sim = _soul_similarity(candidate.soul_canonical, other.soul_canonical)
        else:
            sim = _digest_similarity(candidate.soul_digest, other.soul_digest)

        if digest_equal and set(candidate.skills) == set(other.skills):
            status = "exact_duplicate"
            needs_confirm = True
        elif sim >= 0.9:
            status = "near_duplicate"
            needs_confirm = False
        elif not diffs:
            status = "irrelevant_difference"
            needs_confirm = False
        else:
            status = "meaningful_difference"
            needs_confirm = False

        result = DistinctivenessResult(
            candidate=candidate.profile or "default",
            closest_profile=other.profile,
            similarity=sim,
            status=status,
            differences=diffs,
            needs_confirmation=needs_confirm,
            decision="pending" if needs_confirm else "run",
        )
        if best is None or result.similarity > best.similarity:
            best = result
    return best or DistinctivenessResult(candidate=candidate.profile or "default")


def preflight_check(
    candidate_name: str,
    existing_names: Iterable[str],
) -> DistinctivenessResult:
    """Run the full preflight check for a candidate profile."""
    candidate = load_profile_config(candidate_name if candidate_name != "default" else None)
    others = [
        load_profile_config(name if name != "default" else None)
        for name in existing_names
        if name != candidate_name
    ]
    return compare_profiles(candidate, others)


# ---------------------------------------------------------------------------
# Budget accounting
# ---------------------------------------------------------------------------


@dataclass
class Budget:
    """Execution budget for a run or run set."""

    max_profiles: int = 8
    max_agent_iterations: int = 20
    max_model_calls: int = 40
    max_tool_calls: int = 60
    max_wall_time_seconds: int = 1200
    max_output_tokens: int = 12000

    profiles_used: int = 0
    agent_iterations_used: int = 0
    model_calls_used: int = 0
    tool_calls_used: int = 0
    output_tokens_used: int = 0
    started_at: datetime | None = None

    def exceeded(self) -> bool:
        if self.profiles_used > self.max_profiles:
            return True
        if self.agent_iterations_used > self.max_agent_iterations:
            return True
        if self.model_calls_used > self.max_model_calls:
            return True
        if self.tool_calls_used > self.max_tool_calls:
            return True
        if self.output_tokens_used > self.max_output_tokens:
            return True
        if self.started_at:
            elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
            if elapsed > self.max_wall_time_seconds:
                return True
        return False

    def wall_time_exceeded(self) -> bool:
        if not self.started_at:
            return False
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed > self.max_wall_time_seconds


# ---------------------------------------------------------------------------
# Append-only record writer
# ---------------------------------------------------------------------------


class RecordWriter:
    """Append-only JSONL writer with ledger generation support."""

    def __init__(self, profile: str | None = None):
        self.profile = profile
        self.data_dir = moacubed_dir(profile)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _append(self, filename: str, record: dict[str, Any]) -> Path:
        path = self.data_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return path

    def write_review(self, record: dict[str, Any]) -> Path:
        record.setdefault("schema_version", REVIEW_SCHEMA_VERSION)
        return self._append("reviews.jsonl", record)

    def write_run(self, record: dict[str, Any]) -> Path:
        record.setdefault("schema_version", RUN_SCHEMA_VERSION)
        return self._append("levelsets.jsonl", record)

    def write_targeted_test(self, record: dict[str, Any]) -> Path:
        record.setdefault("schema_version", RUN_SCHEMA_VERSION)
        return self._append("targeted-tests.jsonl", record)

    def write_recommendation(self, record: dict[str, Any]) -> Path:
        record.setdefault("schema_version", RECOMMENDATION_SCHEMA_VERSION)
        return self._append("recommendations.jsonl", record)

    def write_preflight(self, record: dict[str, Any]) -> Path:
        record.setdefault("schema_version", PREFLIGHT_SCHEMA_VERSION)
        return self._append("preflight.jsonl", record)


# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """Return the current time as an RFC3339 UTC string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Ledger generation
# ---------------------------------------------------------------------------


def generate_ledger(profile: str | None = None) -> str:
    """Generate a human-readable moacubed.md ledger for the profile."""
    home = profile_home(profile)
    data_dir = moacubed_dir(profile)
    config = load_profile_config(profile)
    fp = config.fingerprint()

    lines: list[str] = []
    lines.append(f"# MoACubed — {profile or 'default'}")
    lines.append("")
    lines.append("## Profile Identity")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Profile | `{profile or 'default'}` |")
    lines.append(f"| Configuration fingerprint | `{fp}` |")
    lines.append(f"| SOUL.md digest | `{config.soul_digest}` |")
    lines.append(f"| Skills | {', '.join(f'`{s}`' for s in config.skills) or 'none'} |")
    lines.append("")

    lines.append("## Capability Summary")
    lines.append("")
    lines.append("| Domain | Score | Confidence | Samples | Last tested |")
    lines.append("|---|---:|---:|---:|---|")
    lines.append("| — | — | none | 0 | — |")
    lines.append("")

    lines.append("## Level-Set Results")
    lines.append("")
    lines.append("| Baseline | Version | Run ID | Score | Status | Date |")
    lines.append("|---|---|---|---|---|---|")
    if (data_dir / "levelsets.jsonl").exists():
        for raw in (data_dir / "levelsets.jsonl").read_text().splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            lines.append(
                f"| `{rec.get('baseline_id', '-')}` | `{rec.get('baseline_version', '-')}` "
                f"| `{rec.get('run_id', '-')}` | {rec.get('overall_score', '-')} "
                f"| {rec.get('status', '-')} | {rec.get('finished_at', '-')} |"
            )
    else:
        lines.append("| — | — | — | — | — | — |")
    lines.append("")

    lines.append("## Targeted Test Results")
    lines.append("")
    lines.append("| Test ID | Source review | Capability | Result | Confidence |")
    lines.append("|---|---|---|---|---|")
    if (data_dir / "targeted-tests.jsonl").exists():
        for raw in (data_dir / "targeted-tests.jsonl").read_text().splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            lines.append(
                f"| `{rec.get('run_id', '-')}` | `{rec.get('source_review_id', '-')}` "
                f"| `{rec.get('capability', '-')}` | {rec.get('result', '-')} "
                f"| {rec.get('confidence', '-')} |"
            )
    else:
        lines.append("| — | — | — | — | — |")
    lines.append("")

    lines.append("## Human Feedback Summary")
    lines.append("")
    lines.append("| Review ID | Task | Outcome | Key finding |")
    lines.append("|---|---|---|---|")
    if (data_dir / "reviews.jsonl").exists():
        for raw in (data_dir / "reviews.jsonl").read_text().splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            lines.append(
                f"| `{rec.get('review_id', '-')}` | `{rec.get('task_id', '-')}` "
                f"| {rec.get('human', {}).get('final_outcome', '-')} | "
                f"{rec.get('human', {}).get('comment', '-')} |"
            )
    else:
        lines.append("| — | — | — | — |")
    lines.append("")

    lines.append("## Routing Recommendations")
    lines.append("")
    lines.append("| Recommendation | Domain | Confidence | Status |")
    lines.append("|---|---|---|---|")
    if (data_dir / "recommendations.jsonl").exists():
        for raw in (data_dir / "recommendations.jsonl").read_text().splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            lines.append(
                f"| `{rec.get('recommendation_id', '-')}` | `{rec.get('domain', '-')}` "
                f"| {rec.get('confidence', '-')} | {rec.get('status', '-')} |"
            )
    else:
        lines.append("| — | — | — | — |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"_Generated: {now_iso()}_")
    lines.append("")
    return "\n".join(lines)


def write_ledger(profile: str | None = None) -> Path:
    """Generate and write the profile's moacubed.md ledger."""
    path = ledger_path(profile)
    path.write_text(generate_ledger(profile), encoding="utf-8")
    return path
