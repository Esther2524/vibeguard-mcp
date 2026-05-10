"""Implementation of the `complete_handoff` MCP tool.

NEW STRUCTURED CONTRACT (v0.3): the input is no longer keyed by question_id.
The host agent (driven by the vibeguard-interview skill) interviews the user
in its own words, then synthesizes the answers into structured input:

    complete_handoff(
        workspace_id="...",
        approved_advisories=["fe_be_separation"],
        scope_globs=["app/**", "components/**"],
        persona_summary="non-technical merchant",
        contractor_handle="sarah",       # optional: overrides contractor_id from start
        notes="..."                      # optional: anything else to record
    )
"""
import json
import os
import pathlib
from datetime import date

from core.kb import KB
from core.patches import apply_patch_set, patch_set_for_advisory
from core.sanitizer import sanitize_to_workspace
from templates.contractor_brief import render_contractor_brief
from templates.owner_memory import render_owner_memory

PATCHES_ROOT = os.path.join(os.path.dirname(__file__), "..", "patches")
WORKSPACES_ROOT = os.path.expanduser("~/vibeguard-workspaces")

DEFAULT_FORBIDDEN = [".env*", "secrets/**", "infra/**", "src/backend/**"]


def complete_handoff_impl(
    kb: KB,
    workspace_id: str,
    approved_advisories: list[str] | None = None,
    scope_globs: list[str] | None = None,
    persona_summary: str | None = None,
    contractor_handle: str | None = None,
    notes: str | None = None,
) -> dict:
    handoff = kb.get_handoff(workspace_id)
    if not handoff:
        return {"error": f"Unknown workspace_id {workspace_id}. Call start_handoff first."}

    approved_advisories = approved_advisories or []
    scope_globs = scope_globs or [
        "app/**", "components/**", "pages/**", "src/frontend/**",
        "public/**", "package.json", "*.config.*",
    ]
    persona_summary = persona_summary or "Non-technical owner."
    contractor = contractor_handle or handoff["contractor_id"]

    manifest_id = handoff["manifest_id"]
    manifest = kb.get_manifest(manifest_id)
    codebase_path = manifest["codebase_path"]

    # 1) Apply hardcoded refactor patches for any approved advisory
    applied_changes: list[dict] = []
    for advisory_id in approved_advisories:
        patch_set = patch_set_for_advisory(PATCHES_ROOT, advisory_id)
        if patch_set is None:
            continue
        result = apply_patch_set(codebase_path, patch_set)
        for fn in result["applied"]:
            applied_changes.append({
                "advisory": advisory_id,
                "file": fn,
                "kind": "REFACTOR",
                "description": f"Applied {patch_set['name']} patch: {fn}",
            })
        for failure in result["failed"]:
            applied_changes.append({
                "advisory": advisory_id,
                "file": failure["filename"],
                "kind": "REFACTOR_FAILED",
                "description": f"Patch failed: {failure['stderr'].strip()[:160]}",
            })

    # 2) Generate sanitized contractor workspace
    workspace_path = os.path.join(WORKSPACES_ROOT, f"{contractor}-{workspace_id}")
    secrets_for_sanitize = [
        {"real_value": s["value"], "mock_value": s["mock_value"]}
        for s in kb.get_secrets(manifest_id)
        if s.get("mock_value")
    ]
    summary = sanitize_to_workspace(codebase_path, workspace_path, secrets_for_sanitize, scope_globs)

    # 3) Write owner-memory.md in OWNER's project root
    owner_memory_path = os.path.join(codebase_path, "vibeguard-owner-memory.md")
    existing = None
    if os.path.exists(owner_memory_path):
        existing = pathlib.Path(owner_memory_path).read_text()
    secrets_count = len(kb.get_secrets(manifest_id))
    pii_count = len(kb.get_pii(manifest_id))
    owner_md = render_owner_memory(
        existing_md=existing,
        persona=persona_summary,
        codebase_facts={
            "stack": "auto-detected",
            "sensitive_files": list({s["file"] for s in kb.get_secrets(manifest_id)})[:5],
        },
        new_handoff={
            "date": date.today().isoformat(),
            "contractor": contractor,
            "feature": handoff["intent"],
            "approved": approved_advisories,
            "workspace": workspace_path,
        },
    )
    pathlib.Path(owner_memory_path).write_text(owner_md)

    # 4) Write contractor-brief.md inside workspace
    brief_path = os.path.join(workspace_path, "vibeguard-contractor-brief.md")
    contractor_md = render_contractor_brief(
        contractor=contractor,
        feature=handoff["intent"],
        scope_globs=scope_globs,
        forbidden_files=DEFAULT_FORBIDDEN,
        mocks_summary=(
            f"All API keys ({secrets_count} total) replaced with `sk_mock_VIBEGUARD_*` placeholders. "
            f"PII columns ({pii_count} total) replaced with realistic Faker values."
        ),
    )
    pathlib.Path(brief_path).write_text(contractor_md)

    # 5) Persist handoff state
    record = {
        "approved_advisories": approved_advisories,
        "scope_globs": scope_globs,
        "persona_summary": persona_summary,
        "notes": notes,
    }
    kb.save_handoff_answers(workspace_id, json.dumps(record), workspace_path)

    return {
        "workspace_path": workspace_path,
        "contractor_brief_path": brief_path,
        "owner_memory_path": owner_memory_path,
        "applied_changes": applied_changes,
        "approved_advisories": approved_advisories,
        "mock_count": summary["mocks_applied"],
        "redaction_count": pii_count,
        "files_in_workspace": summary["files_copied"],
    }
