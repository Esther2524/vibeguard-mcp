"""Thin LLM backend abstraction. v0 ships an Anthropic Claude implementation."""
import json
import os
from anthropic import Anthropic

# Lazy client init — don't blow up on import if API key isn't set yet
_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it before calling VibeGuard tools."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def llm_json(prompt: str, system: str = "Return only valid JSON.", model: str = "claude-sonnet-4-5-20250929", max_tokens: int = 2048) -> dict | list:
    """Call Claude, expect JSON response, parse and return."""
    client = _get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip ```json ... ``` fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return json.loads(text)
