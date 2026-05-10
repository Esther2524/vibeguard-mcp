"""Implementation of the `start_handoff` MCP tool.

This tool does NO question generation and NO LLM calls. It returns:
  - The codebase manifest summary (what's sensitive, what's where)
  - The list of privacy advisories applicable to this codebase
  - A workspace_id to thread through to complete_handoff

The host agent (Cursor / Claude Code), guided by the
`vibeguard-interview.skill.md`, decides what questions to ask the user
and how to phrase them.
"""
from core.advisories import applicable_advisories
from core.kb import KB


def _manifest_summary(kb: KB, manifest_id: str) -> dict:
    secrets = kb.get_secrets(manifest_id)
    pii = kb.get_pii(manifest_id)
    return {
        "SECRETS": {
            "count": len(secrets),
            "items": [{"file": s["file"], "kind": s["kind"]} for s in secrets[:20]],
        },
        "PII": {
            "count": len(pii),
            "items": [{"file": p["file"], "kind": p["kind"]} for p in pii[:20]],
        },
    }


def start_handoff_impl(kb: KB, intent: str, contractor_id: str | None) -> dict:
    manifest_id = kb.latest_manifest_id()
    if not manifest_id:
        return {"error": "No manifest found. Call register_codebase first."}

    summary = _manifest_summary(kb, manifest_id)
    secret_kinds = [s["kind"] for s in summary["SECRETS"]["items"]]
    advisories = applicable_advisories(secret_kinds)
    handoff_id = kb.create_handoff(manifest_id, contractor_id or "unknown", intent)

    return {
        "workspace_id": handoff_id,
        "manifest_summary": summary,
        "available_advisories": advisories,
        "guidance": (
            "Use the vibeguard-interview skill to conduct the user interview. "
            "Once the user has answered, call complete_handoff with structured input "
            "(approved_advisories, scope_globs, persona_summary)."
        ),
    }
