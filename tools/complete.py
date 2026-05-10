"""Implementation of the `complete_handoff` MCP tool — the heart of the demo."""
import json
import os
import pathlib
from datetime import date

from core.kb import KB
from core.patches import apply_patch_set, patch_set_for_answers
from core.sanitizer import sanitize_to_workspace
from templates.contractor_brief import render_contractor_brief
from templates.owner_memory import render_owner_memory

PATCHES_ROOT = os.path.join(os.path.dirname(__file__), "..", "patches")
WORKSPACES_ROOT = os.path.expanduser("~/vibeguard-workspaces")


def _determine_scope(answers: list[dict]) -> list[str] | None:
    """Look for scope hints in answers; default to a reasonable front-end scope."""
    for a in answers:
        ans = (a.get("answer") or "").lower()
        if "front" in ans or "frontend" in ans or "fe" in ans.split():
            return [
                "app/**", "components/**", "pages/**", "src/frontend/**",
                "public/**", "package.json", "*.config.*", "*.config.js",
                "tsconfig.json", "tailwind.config.*",
            ]
    # default scope is broad — caller can refine via the SCOPE question
    return [
        "app/**", "components/**", "pages/**", "src/frontend/**",
        "public/**", "package.json",
    ]


def _extract_persona(answers: list[dict]) -> str | None:
    for a in answers:
        if a.get("question_id", "").startswith("persona"):
            return a.get("answer")
    return None


def _extract_approved_advisories(answers: list[dict]) -> list[str]:
    out = []
    for a in answers:
        qid = a.get("question_id", "")
        ans = (a.get("answer") or "").lower()
        if qid.startswith("advisory") and ans.startswith("yes"):
            label = qid.replace("advisory_", "").replace("_", " ").upper()
            out.append(label)
    return out


def complete_handoff_impl(kb: KB, workspace_id: str, answers: list[dict]) -> dict:
    handoff = kb.get_handoff(workspace_id)
    if not handoff:
        return {"error": f"Unknown workspace_id {workspace_id}. Call start_handoff first."}

    manifest_id = handoff["manifest_id"]
    contractor = handoff["contractor_id"]

    manifest = kb.get_manifest(manifest_id)
    codebase_path = manifest["codebase_path"]

    # 1) Apply hardcoded refactor patches if owner approved any architectural advisories
    patch_set = patch_set_for_answers(PATCHES_ROOT, answers)
    applied_changes: list[dict] = []
    if patch_set:
        result = apply_patch_set(codebase_path, patch_set)
        for fn in result["applied"]:
            applied_changes.append({
                "file": fn,
                "kind": "REFACTOR",
                "description": f"Applied {patch_set['name']} patch: {fn}",
                "diff": "",
            })
        for failure in result["failed"]:
            applied_changes.append({
                "file": failure["filename"],
                "kind": "REFACTOR_FAILED",
                "description": f"Patch failed: {failure['stderr'].strip()[:120]}",
                "diff": "",
            })

    # 2) Generate sanitized contractor workspace
    workspace_path = os.path.join(WORKSPACES_ROOT, f"{contractor}-{workspace_id}")
    secrets_for_sanitize = [
        {"real_value": s["value"], "mock_value": s["mock_value"]}
        for s in kb.get_secrets(manifest_id)
        if s.get("mock_value")
    ]
    scope_globs = _determine_scope(answers)
    summary = sanitize_to_workspace(codebase_path, workspace_path, secrets_for_sanitize, scope_globs)

    # 3) Write owner-memory.md in OWNER's project root
    owner_memory_path = os.path.join(codebase_path, "vibeguard-owner-memory.md")
    existing = None
    if os.path.exists(owner_memory_path):
        existing = pathlib.Path(owner_memory_path).read_text()
    persona = _extract_persona(answers) or "Non-technical owner."
    approved = _extract_approved_advisories(answers)
    secrets_count = len(kb.get_secrets(manifest_id))
    pii_count = len(kb.get_pii(manifest_id))
    owner_md = render_owner_memory(
        existing_md=existing,
        persona=persona,
        codebase_facts={
            "stack": "auto-detected",
            "sensitive_files": list({s["file"] for s in kb.get_secrets(manifest_id)})[:5],
        },
        new_handoff={
            "date": date.today().isoformat(),
            "contractor": contractor,
            "feature": handoff["intent"],
            "approved": approved,
            "workspace": workspace_path,
        },
    )
    pathlib.Path(owner_memory_path).write_text(owner_md)

    # 4) Write contractor-brief.md in workspace root
    brief_path = os.path.join(workspace_path, "vibeguard-contractor-brief.md")
    contractor_md = render_contractor_brief(
        contractor=contractor,
        feature=handoff["intent"],
        scope_globs=scope_globs or ["**/*"],
        forbidden_files=[".env*", "secrets/**", "infra/**", "src/backend/**"],
        mocks_summary=(
            f"All API keys ({secrets_count} total) replaced with `sk_mock_VIBEGUARD_*` placeholders. "
            f"PII columns ({pii_count} total) replaced with realistic Faker values."
        ),
    )
    pathlib.Path(brief_path).write_text(contractor_md)

    # 5) Persist handoff state
    kb.save_handoff_answers(workspace_id, json.dumps(answers), workspace_path)

    return {
        "workspace_path": workspace_path,
        "contractor_brief_path": brief_path,
        "owner_memory_path": owner_memory_path,
        "applied_changes": applied_changes,
        "mock_count": summary["mocks_applied"],
        "redaction_count": pii_count,
        "files_in_workspace": summary["files_copied"],
    }
