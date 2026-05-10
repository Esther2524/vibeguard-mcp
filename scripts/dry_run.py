#!/usr/bin/env python3
"""Run the full VibeGuard handoff flow without Cursor.

Useful for: rehearsal verification, regression checking, debugging the
patches/sanitizer when you don't want to spin up Cursor.

Usage:  python scripts/dry_run.py <path-to-demo-codebase>
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.kb import KB                                # noqa: E402
from tools.complete import complete_handoff_impl      # noqa: E402
from tools.register import register_codebase_impl     # noqa: E402
from tools.start import start_handoff_impl            # noqa: E402

KB_PATH = os.path.expanduser("~/.vibeguard/kb.json")


def banner(title: str) -> None:
    print(f"\n{'═' * 64}")
    print(f"  {title}")
    print(f"{'═' * 64}")


def main() -> None:
    ap = argparse.ArgumentParser(description="VibeGuard end-to-end dry run.")
    ap.add_argument("codebase", help="path to demo codebase")
    ap.add_argument("--contractor", default="sarah", help="contractor name (default: sarah)")
    ap.add_argument("--intent", default="hand off the front-end to sarah", help="user intent")
    args = ap.parse_args()

    if not os.path.isdir(args.codebase):
        print(f"❌ codebase path does not exist: {args.codebase}", file=sys.stderr)
        sys.exit(1)

    kb = KB(KB_PATH)

    # ─────── PHASE 1 ───────
    banner(f"PHASE 1 — register_codebase({args.codebase})")
    r = register_codebase_impl(kb, args.codebase)
    print(f"  manifest_id : {r['manifest_id'][:8]}…")
    print(f"  secrets     : {r['zones']['SECRETS']['count']}")
    print(f"  pii         : {r['zones']['PII']['count']}")
    for s in r["zones"]["SECRETS"]["items"][:5]:
        print(f"    · {s['file']}:{s['locator']:5s} → {s['kind']}")

    # ─────── PHASE 2 ───────
    banner("PHASE 2 — start_handoff(...)")
    s = start_handoff_impl(kb, args.intent, args.contractor)
    print(f"  workspace_id : {s['workspace_id']}")
    sm = s["manifest_summary"]
    print(f"  context      : {sm['SECRETS']['count']} secrets, {sm['PII']['count']} PII columns")
    print(f"  advisories:")
    for a in s["available_advisories"]:
        marker = "✓" if a["current_status"] == "applicable" else " "
        print(f"    {marker} {a['id']:25s} [{a['current_status']}]")

    # Choose which advisories to approve in this dry run
    approved = [a["id"] for a in s["available_advisories"] if a["current_status"] == "applicable"]

    # ─────── PHASE 3a ─────── (preview)
    banner("PHASE 3a — complete_handoff (PREVIEW, confirm=False)")
    preview = complete_handoff_impl(
        kb,
        workspace_id=s["workspace_id"],
        approved_advisories=approved,
        scope_globs=["src/**", "package.json", ".env.example", "vite.config.ts", "tsconfig.json"],
        persona_summary=f"Non-technical owner outsourcing to {args.contractor}",
        contractor_handle=args.contractor,
        confirm=False,
    )
    print(f"  preview      : {preview.get('preview')}")
    print(f"  executed     : {preview.get('executed')}")
    print(f"  summary_for_user:")
    print(f"    {preview['plan']['summary_for_user']}")
    print(f"  files in OWNER repo that will change ({len(preview['plan']['will_modify_owner_codebase'])}):")
    for f in preview["plan"]["will_modify_owner_codebase"]:
        print(f"    · {f}")

    # ─────── PHASE 3b ─────── (execute)
    banner("PHASE 3b — complete_handoff (EXECUTE, confirm=True)")
    c = complete_handoff_impl(
        kb,
        workspace_id=s["workspace_id"],
        approved_advisories=approved,
        scope_globs=["src/**", "package.json", ".env.example", "vite.config.ts", "tsconfig.json"],
        persona_summary=f"Non-technical owner outsourcing to {args.contractor}",
        contractor_handle=args.contractor,
        confirm=True,
    )
    print(f"  executed         : {c.get('executed')}")
    print(f"  workspace        : {c['workspace_path']}")
    print(f"  applied changes  : {len(c['applied_changes'])}")
    for chg in c["applied_changes"]:
        marker = "✓" if chg["kind"] == "REFACTOR" else "✗"
        print(f"    {marker} [{chg['advisory']:18s}] {chg['file']}")
    print(f"  files in workspace : {c['files_in_workspace']}")
    print(f"  mocks applied      : {c['mock_count']}")
    print(f"  owner memory at    : {c['owner_memory_path']}")
    print(f"  contractor brief at: {c['contractor_brief_path']}")

    banner("✅  DRY RUN COMPLETE")
    print(f"  inspect kb : cat {KB_PATH} | python -m json.tool | head -60")
    print(f"  workspace  : ls {c['workspace_path']}")
    print(f"  to redo    : scripts/quickstart.sh")
    print()


if __name__ == "__main__":
    main()
