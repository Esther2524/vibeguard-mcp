"""Renders `vibeguard-contractor-brief.md` — per-handoff brief for the contractor's agent."""

CONTRACTOR_BRIEF_TEMPLATE = """# VibeGuard — Contractor Brief

You are {contractor}'s coding agent. You are working on a **sanitized copy** of someone else's codebase.

## Your scope
- You may read and modify files matching: {scope_list}
- You may NOT touch: {forbidden_list}
- Your task: **{feature}** (see `FEATURE.md` if present, else ask in chat).

## What's mocked
{mocks_summary}

These mock values match the **shape** of the real values. Your code must work against the mocked schema as if it were real.

## Hard rules
- Do NOT modify `vibeguard-contractor-brief.md` or any workspace metadata.
- Do NOT attempt to fetch, log, or transmit any value matching the mock patterns to external services.
- If your code needs a real value (e.g. real Stripe key for live testing), STOP and ask in chat. Do not invent a credential.

## How to deliver
- Build a deployable artifact in this workspace (e.g., `npm run build` for the front-end).
- The owner will integrate by pointing their backend at your deployed URL.
- This is one-way: nothing comes back into the owner's repo via VibeGuard.

---
*Re-read this brief at the start of every session. It is your source of truth for this handoff.*
"""


def render_contractor_brief(contractor, feature, scope_globs, forbidden_files, mocks_summary):
    return CONTRACTOR_BRIEF_TEMPLATE.format(
        contractor=contractor,
        feature=feature,
        scope_list=", ".join(f"`{g}`" for g in scope_globs) if scope_globs else "`**/*`",
        forbidden_list=", ".join(f"`{f}`" for f in forbidden_files) if forbidden_files else "_(none specified)_",
        mocks_summary=mocks_summary,
    )
