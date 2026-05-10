"""Renders `vibeguard-owner-memory.md` — owner's persistent context."""

OWNER_MEMORY_TEMPLATE = """# VibeGuard — Owner Memory

*This file is maintained by VibeGuard. The owner's coding agent should re-read it at the start of every session.*

## Owner profile
{persona}

## Codebase facts (auto-maintained)
- Stack: {stack}
- Sensitive files: {sensitive_files}

## Handoff history
{handoff_history}
"""


def render_owner_memory(existing_md, persona, codebase_facts, new_handoff):
    """Build the markdown for the owner-memory file.

    For v0, history is overwritten with the latest handoff entry. (A future
    version would parse `existing_md` and append.)
    """
    handoff_line = (
        f"- {new_handoff['date']} — outsourced "
        f'"{new_handoff["feature"]}" to {new_handoff["contractor"]}. '
        f"Approved: {', '.join(new_handoff['approved']) or 'none'}. "
        f"Workspace: `{new_handoff['workspace']}`."
    )

    sensitive_files = codebase_facts.get("sensitive_files") or []
    sensitive_str = ", ".join(f"`{f}`" for f in sensitive_files) if sensitive_files else "_none detected_"

    return OWNER_MEMORY_TEMPLATE.format(
        persona=persona,
        stack=codebase_facts.get("stack", "unknown"),
        sensitive_files=sensitive_str,
        handoff_history=handoff_line,
    )
