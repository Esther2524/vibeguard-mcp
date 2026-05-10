"""Implementation of the `start_handoff` MCP tool."""
from core.kb import KB
from core.llm import llm_json
from core.prompts import interview_prompt, INTERVIEW_SYSTEM, FALLBACK_QUESTIONS


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

    # Try LLM-generated questions; fall back to hardcoded set on failure
    try:
        questions = llm_json(interview_prompt(intent, summary), system=INTERVIEW_SYSTEM)
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("LLM returned non-list or empty")
    except Exception as e:
        questions = FALLBACK_QUESTIONS
        warning = f"LLM unavailable, using fallback questions: {type(e).__name__}"
    else:
        warning = None

    handoff_id = kb.create_handoff(manifest_id, contractor_id or "unknown", intent)

    out = {
        "workspace_id": handoff_id,
        "questions": questions,
        "retrieved_context": (
            f"{summary['SECRETS']['count']} secrets, "
            f"{summary['PII']['count']} PII columns detected in codebase."
        ),
    }
    if warning:
        out["warning"] = warning
    return out
