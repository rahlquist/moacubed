"""Real Hermes auxiliary-client adapter for persona-only references."""
from __future__ import annotations
import importlib
import time
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


def _runtime(profile: ProfileContext) -> dict[str, Any]:
    """Resolve provider runtime without persisting credentials."""
    try:
        resolver = importlib.import_module("hermes_cli.runtime_provider")
        return resolver.resolve_runtime_provider(requested=profile.provider, target_model=profile.model)
    except Exception:
        return {"provider": profile.provider, "model": profile.model}


def call_reference(profile: ProfileContext, prompt: str, options: MoAOptions) -> ReferenceResult:
    """Call a reference through Hermes' existing auxiliary client.

    This adapter deliberately supplies no tools and passes only the constructed
    persona/task prompt. It never launches the profile's skills or agent loop.
    """
    started = time.monotonic()
    try:
        auxiliary = importlib.import_module("agent.auxiliary_client")
        runtime = _runtime(profile)
        runtime.pop("provider", None)
        runtime.pop("model", None)
        response = auxiliary.call_llm(
            task="moa_reference",
            messages=[{"role": "system", "content": "You are a tool-free advisory reference."},
                      {"role": "user", "content": prompt}],
            tools=None,
            provider=profile.provider,
            model=profile.model,
            max_tokens=options.reference_max_tokens,
            timeout=options.reference_timeout_seconds,
            reasoning_config=(
                {"effort": profile.reasoning_effort}
                if profile.reasoning_effort else None
            ),
            **runtime,
        )
        output = _text(response)
        return _result(profile=profile.name, persona_digest=profile.persona_digest,
                       output=output, status="passed", output_tokens=_usage_tokens(response),
                       wall_time_seconds=round(time.monotonic() - started, 3))
    except TimeoutError as exc:
        return _result(profile=profile.name, persona_digest=profile.persona_digest,
                       status="timeout", error=str(exc), wall_time_seconds=round(time.monotonic() - started, 3))
    except Exception as exc:
        return _result(profile=profile.name, persona_digest=profile.persona_digest,
                       status="failed", error=str(exc), wall_time_seconds=round(time.monotonic() - started, 3))
