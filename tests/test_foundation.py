"""Tests for the MoACubed foundation module."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure moacubed is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moacubed.foundation import (  # noqa: E402
    Budget,
    ProfileConfig,
    _canonicalize_dict,
    _digest,
    _jaccard,
    _normalize_whitespace,
    _soul_similarity,
    compare_profiles,
    load_profile_config,
    preflight_check,
)


def test_normalize_whitespace():
    assert _normalize_whitespace("  hello   world  ") == "hello world"
    assert _normalize_whitespace("hello\n\nworld") == "hello world"


def test_digest_stable():
    a = _digest({"x": 1, "y": 2})
    b = _digest({"y": 2, "x": 1})
    assert a == b


def test_canonicalize_dict_drops_ephemeral():
    d = {"name": "foo", "created_at": "now", "updated_at": "later"}
    out = _canonicalize_dict(d)
    assert "created_at" not in out
    assert "updated_at" not in out
    assert out["name"] == "foo"


def test_canonicalize_dict_sorts_lists():
    d = {"skills": ["b", "a", "c"]}
    out = _canonicalize_dict(d)
    assert out["skills"] == ["a", "b", "c"]


def test_jaccard():
    assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert _jaccard({"a"}, {"b"}) == 0.0
    assert _jaccard(set(), set()) == 1.0
    assert _jaccard({"a"}, set()) == 0.0


def test_soul_similarity_identical():
    assert _soul_similarity("hello world", "hello world") == 1.0


def test_soul_similarity_different():
    sim = _soul_similarity("hello world", "foo bar baz")
    assert 0.0 <= sim < 1.0


def test_soul_similarity_none():
    assert _soul_similarity(None, None) == 1.0
    assert _soul_similarity("hello", None) == 0.0


def test_profile_config_fingerprint_stable():
    a = ProfileConfig(profile="foo", skills=["x", "y"])
    b = ProfileConfig(profile="foo", skills=["y", "x"])
    assert a.fingerprint() == b.fingerprint()


def test_compare_profiles_exact_duplicate():
    a = ProfileConfig(profile="a", soul_digest="abc", skills=["x", "y"])
    b = ProfileConfig(profile="b", soul_digest="abc", skills=["x", "y"])
    result = compare_profiles(a, [b])
    assert result.status == "exact_duplicate"
    assert result.needs_confirmation is True


def test_compare_profiles_meaningful_difference():
    a = ProfileConfig(profile="a", soul_digest="abc", skills=["x"])
    b = ProfileConfig(profile="b", soul_digest="xyz", skills=["y", "z"])
    result = compare_profiles(a, [b])
    assert result.status == "meaningful_difference"
    assert result.needs_confirmation is False


def test_compare_profiles_no_others():
    a = ProfileConfig(profile="a", soul_digest="abc")
    result = compare_profiles(a, [])
    assert result.status == "meaningful_difference"
    assert result.decision == "run"


def test_budget_not_exceeded():
    b = Budget(max_profiles=2, max_model_calls=10)
    b.profiles_used = 1
    b.model_calls_used = 5
    assert b.exceeded() is False


def test_budget_exceeded():
    b = Budget(max_profiles=2)
    b.profiles_used = 3
    assert b.exceeded() is True


def test_preflight_check_identical(tmp_path, monkeypatch):
    """End-to-end test: two identical profiles trigger exact_duplicate."""
    home = tmp_path / ".hermes"
    home.mkdir()

    # Create profile A
    profile_a = home / "profiles" / "a"
    profile_a.mkdir(parents=True)
    (profile_a / "SOUL.md").write_text("# Profile A\n\nIdentity: Test\n")

    # Create profile B (identical SOUL.md)
    profile_b = home / "profiles" / "b"
    profile_b.mkdir(parents=True)
    (profile_b / "SOUL.md").write_text("# Profile A\n\nIdentity: Test\n")

    monkeypatch.setenv("HERMES_HOME", str(home))

    result = preflight_check("a", ["b"])
    assert result.status == "exact_duplicate"
    assert result.needs_confirmation is True


def test_preflight_check_distinct(tmp_path, monkeypatch):
    """End-to-end test: different profiles proceed."""
    home = tmp_path / ".hermes"
    home.mkdir()

    profile_a = home / "profiles" / "a"
    profile_a.mkdir(parents=True)
    (profile_a / "SOUL.md").write_text("# Profile A\n\nIdentity: Alpha\n")

    profile_b = home / "profiles" / "b"
    profile_b.mkdir(parents=True)
    (profile_b / "SOUL.md").write_text("# Profile B\n\nIdentity: Beta\n")

    monkeypatch.setenv("HERMES_HOME", str(home))

    result = preflight_check("a", ["b"])
    assert result.status == "meaningful_difference"
    assert result.needs_confirmation is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
