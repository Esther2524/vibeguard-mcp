"""VibeGuard MCP server — entry point.

Three tools that any MCP-compatible host (Cursor, Claude Desktop, etc.)
can call. The companion `skills/vibeguard-interview.skill.md` orchestrates
the user-facing conversation; this server is pure mechanism.

Run with: python server.py
"""
import os

from mcp.server.fastmcp import FastMCP

from core.kb import KB
from tools.complete import complete_handoff_impl
from tools.register import register_codebase_impl
from tools.start import start_handoff_impl

mcp = FastMCP("vibeguard")

KB_PATH = os.path.expanduser("~/.vibeguard/kb.json")
os.makedirs(os.path.dirname(KB_PATH), exist_ok=True)
_kb = KB(KB_PATH)


@mcp.tool()
def register_codebase(codebase_path: str, incremental: bool = False) -> dict:
    """Scan an existing codebase and classify sensitive items into privacy zones.

    Walks the codebase, finds secrets (Stripe / AWS / OpenAI / etc keys) via regex
    and PII columns (email / ssn / address / etc) via SQL schema parsing, then
    persists a manifest to the local KB at ~/.vibeguard/kb.json.

    Required before start_handoff can be called.

    Args:
        codebase_path: absolute path to the project root.
        incremental: reserved for future use.
    """
    return register_codebase_impl(_kb, codebase_path)


@mcp.tool()
def start_handoff(intent: str, contractor_id: str = "unknown") -> dict:
    """Begin a contractor handoff. Returns the manifest summary + applicable advisories.

    The MCP does NOT generate questions itself. The host agent (Cursor / Claude
    Code) is expected to use the `vibeguard-interview` skill to interview the
    user, then synthesize structured input for complete_handoff.

    Args:
        intent: the user's stated goal, e.g. "hand off the front-end to Sarah".
        contractor_id: short handle for the contractor (used in workspace path).

    Returns:
        workspace_id: thread this through to complete_handoff.
        manifest_summary: detected secrets + PII counts and samples.
        available_advisories: list of privacy improvements applicable to this codebase,
                              each with id / label / summary / current_status.
        guidance: brief reminder to use the skill for the interview.
    """
    return start_handoff_impl(_kb, intent, contractor_id)


@mcp.tool()
def complete_handoff(
    workspace_id: str,
    approved_advisories: list[str] | None = None,
    scope_globs: list[str] | None = None,
    persona_summary: str | None = None,
    contractor_handle: str | None = None,
    notes: str | None = None,
    confirm: bool = False,
) -> dict:
    """Plan or execute the handoff. TWO-PHASE:

    PHASE 1 — preview (confirm=False, default):
        Returns the plan. Lists which files in the owner's real codebase
        will be modified, which patches will apply, where the workspace
        will be created. No side effects. Show this to the user.

    PHASE 2 — execute (confirm=True):
        Actually applies the patches, generates the sanitized workspace,
        writes vibeguard-owner-memory.md (in owner's project root) and
        vibeguard-contractor-brief.md (inside the workspace).

    The two-phase contract forces you (the host agent) to surface the
    destructive plan to the user before doing it.

    Args:
        workspace_id: from start_handoff.
        approved_advisories: e.g. ["fe_be_separation"]. Each triggers any
            patches in patches/<advisory_id>/.
        scope_globs: file globs the contractor needs. Defaults to a reasonable
            front-end scope.
        persona_summary: brief note on the owner's technical level.
        contractor_handle: optional override for the contractor name.
        notes: any extra context to record.
        confirm: must be True to actually execute. Default False = preview only.

    Idempotent: re-call with the same workspace_id and updated args to revise.
    """
    return complete_handoff_impl(
        _kb,
        workspace_id=workspace_id,
        approved_advisories=approved_advisories,
        scope_globs=scope_globs,
        persona_summary=persona_summary,
        contractor_handle=contractor_handle,
        notes=notes,
        confirm=confirm,
    )


@mcp.tool()
def ping() -> str:
    """Health check — useful for verifying the MCP integration is wired up."""
    return "vibeguard alive"


if __name__ == "__main__":
    mcp.run()
