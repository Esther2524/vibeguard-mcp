"""Implementation of the `start_handoff` MCP tool.

No LLM calls. Returns a 5-question template, customized with the manifest's
real numbers (e.g. "I found 12 secrets including Stripe and AWS").

The host agent (Cursor / Claude Code) is expected to use its own LLM —
ideally guided by the bundled `skills/vibeguard-interview.skill.md` — to
present the questions, follow up, and interpret answers.
"""
from core.kb import KB
from core.prompts import customize_questions


def _manifest_summary(kb: KB, manifest_id: str) -> dict:
    secrets = kb.get_secrets(manifest_id)
    pii = kb.get_pii(manifest_id)
    return {
        "SECRETS": {
            "count": len(secrets),
            "items": [{"file": s["file"], "kind": s["kind"]} for s in secrets[:10]],
        },
        "PII": {
            "count": len(pii),
            "items": [{"file": p["file"], "kind": p["kind"]} for p in pii[:10]],
        },
    }


def start_handoff_impl(kb: KB, intent: str, contractor_id: str | None) -> dict:
    manifest_id = kb.latest_manifest_id()
    if not manifest_id:
        return {"error": "No manifest found. Call register_codebase first."}

    summary = _manifest_summary(kb, manifest_id)
    questions = customize_questions(summary, intent)
    handoff_id = kb.create_handoff(manifest_id, contractor_id or "unknown", intent)

    return {
        "workspace_id": handoff_id,
        "questions": questions,
        "retrieved_context": (
            f"{summary['SECRETS']['count']} secrets, "
            f"{summary['PII']['count']} PII columns detected in codebase."
        ),
        "manifest_summary": summary,  # host agent can use this for richer prompting
    }
