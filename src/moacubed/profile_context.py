"""Profile identity and safe persona context for profile-aware MoA."""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml
from .foundation import hermes_home, profile_home, _normalize_whitespace, discover_profiles

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|ghp|xoxb|xapp|hf)_[A-Za-z0-9._-]{12,}"),
    re.compile(r"(?i)\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----", re.S),
)

@dataclass(frozen=True)
class ProfileContext:
    name: str
    home: Path
    soul_digest: str | None
    persona_digest: str | None
    persona: str
    skills: tuple[str, ...] = ()
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    configuration_fingerprint: str | None = None

    @property
    def short_identity(self) -> dict[str, Any]:
        return {"profile": self.name, "soul_digest": self.soul_digest, "persona_digest": self.persona_digest,
                "provider": self.provider, "model": self.model, "reasoning_effort": self.reasoning_effort,
                "skills": list(self.skills), "configuration_fingerprint": self.configuration_fingerprint}

def sanitize_persona(text: str) -> str:
    result = text
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[redacted secret]", result)
    return result

def _canonical(text: str) -> str:
    return _normalize_whitespace(re.sub(r"^\s*<!--.*?-->\s*$", "", text, flags=re.M | re.S).lower())

def _profile_model(name: str, home: Path) -> tuple[str | None, str | None, str | None]:
    """Read non-secret model identity from a profile config when available."""
    for filename in ("config.yaml", "config.yml"):
        path = home / filename
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            model = data.get("model", {}) if isinstance(data, dict) else {}
            return model.get("provider"), model.get("model") or model.get("name") or model.get("default"), model.get("reasoning_effort")
        except Exception:
            return None, None, None
    return None, None, None


def load_profile_context(name: str) -> ProfileContext:
    home = profile_home(None if name == "default" else name)
    soul_path = home / "SOUL.md"
    raw = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""
    persona = sanitize_persona(raw)
    persona_canonical = _canonical(persona)
    skills_dir = home / "skills"
    skills = tuple(sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists())) if skills_dir.is_dir() else ()
    digest = hashlib.sha256(raw.encode()).hexdigest() if raw else None
    persona_digest = hashlib.sha256(persona_canonical.encode()).hexdigest() if persona_canonical else None
    provider, model, reasoning = _profile_model(name, home)
    config_material = f"{digest}|{provider}|{model}|{reasoning}|{','.join(skills)}"
    fp = hashlib.sha256(config_material.encode()).hexdigest()
    return ProfileContext(name=name, home=home, soul_digest=digest, persona_digest=persona_digest,
                          persona=persona, skills=skills, provider=provider, model=model,
                          reasoning_effort=reasoning, configuration_fingerprint=fp)

def load_profiles(names: list[str]) -> list[ProfileContext]:
    return [load_profile_context(name) for name in names]
