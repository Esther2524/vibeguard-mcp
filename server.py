"""VibeGuard MCP server — entry point.

Exposes 3 tools that any MCP-compatible host (Cursor, Claude Desktop, etc.)
can call:
    - register_codebase
    - start_handoff
    - complete_handoff

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
    """Call this once on a codebase, then again incrementally as files change.

    Scans the codebase and classifies sensitive items into privacy zones
    (SECRETS, PII, BUSINESS_LOGIC, SAFE_TO_SHARE). Persists the classification
    to the CodebaseKB. Required before start_handoff can be called.
    """
    return register_codebase_impl(_kb, codebase_path)


@mcp.tool()
def start_handoff(intent: str, contractor_id: str = "unknown") -> dict:
    """Call this when an owner expresses intent to hand off work to a contractor.

    Retrieves relevant context from the CodebaseKB and returns 5 clarifying
    questions that the host agent should ask the owner. Questions mix
    persona discovery, scope decisions, and privacy education + advisory
    recommendations.

    The host agent presents these to the owner in chat.
    """
    return start_handoff_impl(_kb, intent, contractor_id)


@mcp.tool()
def complete_handoff(workspace_id: str, answers: list[dict]) -> dict:
    """Call this after the owner has answered the 5 questions returned by start_handoff.

    VibeGuard does up to 4 things based on the answers:
    (1) If the owner approved any advisory recommendations (e.g. FE/BE separation),
        actually modifies the owner's real codebase to implement them.
    (2) Generates a sanitized contractor workspace with secrets mocked.
    (3) Updates vibeguard-owner-memory.md in the owner's project root.
    (4) Writes vibeguard-contractor-brief.md inside the contractor workspace.

    Idempotent: re-call with the same workspace_id and updated answers to revise.
    """
    return complete_handoff_impl(_kb, workspace_id, answers)


@mcp.tool()
def ping() -> str:
    """Health check — useful for verifying the MCP integration is wired up."""
    return "vibeguard alive"


if __name__ == "__main__":
    mcp.run()
