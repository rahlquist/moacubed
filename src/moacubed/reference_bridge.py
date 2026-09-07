"""Executed by Hermes' own Python environment for one reference call."""
from __future__ import annotations
import json
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    from agent.auxiliary_client import call_llm
    from hermes_cli.runtime_provider import resolve_runtime_provider

    profile = payload.get("profile") or {}
    provider = profile.get("provider")
    model = profile.get("model")
    runtime = resolve_runtime_provider(requested=provider, target_model=model)
    for key in ("provider", "model"):
        runtime.pop(key, None)
    allowed = {"base_url", "api_key", "main_runtime", "extra_body", "extra_headers", "api_mode", "route_info"}
    runtime = {key: value for key, value in runtime.items() if key in allowed}
    response = call_llm(
        task="moa_reference",
        messages=[
            {"role": "system", "content": "You are a tool-free advisory reference."},
            {"role": "user", "content": payload["prompt"]},
        ],
        tools=None,
        provider=provider,
        model=model,
        max_tokens=payload.get("max_tokens"),
        timeout=payload.get("timeout"),
        reasoning_config=({"effort": profile["reasoning_effort"]} if profile.get("reasoning_effort") else None),
        **runtime,
    )
    text = getattr(response, "output_text", None) or getattr(response, "content", None)
    if not isinstance(text, str):
        try:
            from agent.transports import get_transport
            text = get_transport("chat_completions").normalize_response(response).content or ""
        except Exception:
            choices = getattr(response, "choices", None)
            if choices:
                message = getattr(choices[0], "message", None)
                text = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
            else:
                output = getattr(response, "output", None)
                text = "".join(
                    str(item.get("content", "")) if isinstance(item, dict) else str(item)
                    for item in (output or [])
                )
        if not isinstance(text, str):
            text = str(text or "")
        text = text.strip()
        if not text:
            text = "(empty response)"
    usage = getattr(response, "usage", None)
    tokens = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
    print(json.dumps({"status": "passed", "output": text or "", "output_tokens": tokens}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
