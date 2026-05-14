"""Implementation of the `complete_handoff` MCP tool.

TWO-PHASE CONTRACT (v0.4):

  1. PREVIEW — call with `confirm=False` (default). Returns the plan of
     what would be done (which patches, which files, which workspace path).
     No side effects.

  2. EXECUTE — call again with the SAME args plus `confirm=True`. Actually
     applies the patches, generates the workspace, and writes the markdown
     artifacts.

The two-phase design forces the host agent to surface the destructive
plan to the user before doing it. The skill's Phase 3 walks the agent
through both calls.
"""
import json
import os
import pathlib
from datetime import date

from core.kb import KB
from core.patches import apply_patch_set, files_in_patch, patch_set_for_advisory
from core.sanitizer import sanitize_to_workspace
from templates.contractor_brief import render_contractor_brief
from templates.owner_memory import render_owner_memory

PATCHES_ROOT = os.path.join(os.path.dirname(__file__), "..", "patches")
WORKSPACES_ROOT = os.path.expanduser("~/vibeguard-workspaces")

DEFAULT_FORBIDDEN = [".env*", "secrets/**", "infra/**", "src/backend/**"]
DEFAULT_SCOPE = [
    "app/**", "components/**", "pages/**", "src/frontend/**",
    "src/**", "public/**", "package.json", "*.config.*",
]


def complete_handoff_impl(
    kb: KB,
    workspace_id: str,
    approved_advisories: list[str] | None = None,
    scope_globs: list[str] | None = None,
    persona_summary: str | None = None,
    contractor_handle: str | None = None,
    notes: str | None = None,
    confirm: bool = False,
    forbidden_paths: list[str] | None = None,
) -> dict:
    handoff = kb.get_handoff(workspace_id)
    if not handoff:
        return {"error": f"Unknown workspace_id {workspace_id}. Call start_handoff first."}

    # ----- gather context (no side effects either way) -----
    approved_advisories = approved_advisories or []
    scope_globs = scope_globs or DEFAULT_SCOPE
    persona_summary = persona_summary or "Non-technical owner."
    contractor = contractor_handle or handoff["contractor_id"]

    manifest_id = handoff["manifest_id"]
    manifest = kb.get_manifest(manifest_id)
    codebase_path = manifest["codebase_path"]

    workspace_path = os.path.join(WORKSPACES_ROOT, f"{contractor}-{workspace_id}")
    owner_memory_path = os.path.join(codebase_path, "vibeguard-owner-memory.md")
    contractor_brief_path = os.path.join(workspace_path, "vibeguard-contractor-brief.md")

    # ----- build the plan -----
    patch_sets_to_apply: list[dict] = []
    files_to_modify_in_owner: set[str] = set()
    for advisory_id in approved_advisories:
        ps = patch_set_for_advisory(PATCHES_ROOT, advisory_id)
        if ps is None:
            continue
        patch_sets_to_apply.append(ps)
        for p in ps["patches"]:
            for f in files_in_patch(p["content"]):
                files_to_modify_in_owner.add(f)

    secrets_count = len(kb.get_secrets(manifest_id))
    pii_count = len(kb.get_pii(manifest_id))

    plan = {
        "will_modify_owner_codebase": sorted(files_to_modify_in_owner),
        "patches_to_apply": [
            {
                "advisory": ps["advisory_id"],
                "patch_files": [p["filename"] for p in ps["patches"]],
            }
            for ps in patch_sets_to_apply
        ],
        "will_create_workspace_at": workspace_path,
        "will_write_owner_memory_to": owner_memory_path,
        "will_write_contractor_brief_to": contractor_brief_path,
        "scope_globs_for_workspace": scope_globs,
        "secrets_to_consider": secrets_count,
        "pii_to_consider": pii_count,
        "summary_for_user": _render_plan_summary(
            patch_sets_to_apply, files_to_modify_in_owner, contractor, workspace_path
        ),
    }

    # ----- PREVIEW mode -----
    if not confirm:
        return {
            "preview": True,
            "executed": False,
            "plan": plan,
            "next_step": (
                "Show this plan to the user (especially `summary_for_user` and "
                "`will_modify_owner_codebase`). If they confirm, call complete_handoff "
                "AGAIN with the same arguments plus confirm=true."
            ),
            "warning": (
                "This will modify the owner's real codebase. Always surface the plan "
                "to the user before confirming."
            ),
        }

    # ----- EXECUTE mode (confirm=True) -----
    applied_changes: list[dict] = []
    for ps in patch_sets_to_apply:
        result = apply_patch_set(codebase_path, ps)
        for fn in result["applied"]:
            applied_changes.append({
                "advisory": ps["advisory_id"],
                "file": fn,
                "kind": "REFACTOR",
                "description": f"Applied {ps['name']} patch: {fn}",
            })
        for failure in result["failed"]:
            applied_changes.append({
                "advisory": ps["advisory_id"],
                "file": failure["filename"],
                "kind": "REFACTOR_FAILED",
                "description": f"Patch failed: {failure['stderr'].strip()[:160]}",
            })

    secrets_for_sanitize = [
        {"real_value": s["value"], "mock_value": s["mock_value"]}
        for s in kb.get_secrets(manifest_id)
        if s.get("mock_value")
    ]
    sanitize_summary = sanitize_to_workspace(codebase_path, workspace_path, secrets_for_sanitize, scope_globs)

    existing = pathlib.Path(owner_memory_path).read_text() if os.path.exists(owner_memory_path) else None
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

    merged_forbidden = list(DEFAULT_FORBIDDEN) + (forbidden_paths or [])
    contractor_md = render_contractor_brief(
        contractor=contractor,
        feature=handoff["intent"],
        scope_globs=scope_globs,
        forbidden_files=merged_forbidden,
        mocks_summary=(
            f"All API keys ({secrets_count} total) replaced with `sk_mock_VIBEGUARD_*` placeholders. "
            f"PII columns ({pii_count} total) replaced with realistic Faker values."
        ),
        workspace_path=workspace_path,
        original_repo_path=codebase_path,
    )
    pathlib.Path(contractor_brief_path).write_text(contractor_md)

    record = {
        "approved_advisories": approved_advisories,
        "scope_globs": scope_globs,
        "persona_summary": persona_summary,
        "notes": notes,
    }
    kb.save_handoff_answers(workspace_id, json.dumps(record), workspace_path)

    return {
        "preview": False,
        "executed": True,
        "workspace_path": workspace_path,
        "contractor_brief_path": contractor_brief_path,
        "owner_memory_path": owner_memory_path,
        "applied_changes": applied_changes,
        "approved_advisories": approved_advisories,
        "mock_count": sanitize_summary["mocks_applied"],
        "redaction_count": pii_count,
        "files_in_workspace": sanitize_summary["files_copied"],
    }


def _render_plan_summary(
    patch_sets: list[dict],
    files_to_modify: set[str],
    contractor: str,
    workspace_path: str,
) -> str:
    """Plain-English summary for the host agent to show the user."""
    parts = []
    if patch_sets:
        n_patches = sum(len(ps["patches"]) for ps in patch_sets)
        n_files = len(files_to_modify)
        adv_names = ", ".join(ps["advisory_id"] for ps in patch_sets)
        parts.append(
            f"⚠️ I'll apply {n_patches} refactor patch(es) for [{adv_names}], "
            f"modifying {n_files} file(s) in YOUR REAL CODEBASE: "
            f"{', '.join(sorted(files_to_modify))}."
        )
    else:
        parts.append("ℹ️ No refactor patches will be applied (no approved advisories with patches).")

    parts.append(
        f"📦 I'll generate {contractor}'s sanitized workspace at: {workspace_path}"
    )
    parts.append(
        "📝 I'll write 2 markdown files: vibeguard-owner-memory.md (in your repo) "
        "and vibeguard-contractor-brief.md (in the workspace)."
    )
    parts.append("Proceed? Re-call complete_handoff with confirm=true to execute.")
    return " ".join(parts)
