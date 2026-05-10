# VibeGuard

> **A Privacy Guardian for Vibe Coders.**
> An MCP server that lets non-technical founders safely hand off code to contractors —
> contractor's agent works against a sanitized twin of the codebase, real secrets never cross the line.

Built for the **Cursor Hackathon — *"Build what agents want."***

## What it does

When a non-technical founder ("vibe coder") wants to outsource part of their codebase — typically front-end work — they face a hard choice: hand over the entire repo (the contractor's AI agent now has full access to everything), or spend an evening manually scrubbing secrets and PII out of a fork.

**VibeGuard** replaces both options with three callable MCP tools:

| Tool | What it does |
|---|---|
| `register_codebase(path)` | Walks the codebase, classifies items into `SECRETS` / `PII` / `BUSINESS_LOGIC` / `SAFE_TO_SHARE`, persists to a JSON KB at `~/.vibeguard/kb.json`. |
| `start_handoff(intent, contractor_id)` | Returns 5 LLM-generated clarifying questions mixing persona discovery + scope decisions + **plain-English privacy education** (e.g. *"Want me to set up FE/BE separation? Here's why for privacy…"*). |
| `complete_handoff(workspace_id, answers)` | If the owner approved any architectural advisory (e.g. FE/BE split), **applies a hardcoded refactor patch to the owner's real codebase**, generates a sanitized contractor workspace with shape-preserving mocks, writes `vibeguard-owner-memory.md` (owner-side) and `vibeguard-contractor-brief.md` (contractor-side). |

## Quick start

```bash
# 1. Set up
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Set your LLM key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Wire into Cursor — edit ~/.cursor/mcp.json:
{
  "mcpServers": {
    "vibeguard": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}

# 4. Restart Cursor, then in chat:
# "call vibeguard's ping tool"          → "vibeguard alive"
# "register_codebase on /path/to/repo"  → returns a manifest
# "I want to hand off the front-end to Sarah"
#                                       → agent calls start_handoff, asks you 5 questions
# (you answer)                          → agent calls complete_handoff, refactor + workspace appear
```

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Pact Logic (core IP)                            │
│   classification · interview · advisor logic     │
│   sanitization · workspace generation            │
│   markdown artifact maintenance                  │
├──────────────────────────────────────────────────┤
│  CodebaseKB (JSON file at ~/.vibeguard/kb.json)  │
│   manifests · secrets/PII · mock mappings        │
│   handoff history                                │
├──────────────────────────────────────────────────┤
│  LLMBackend (Anthropic Claude in v0)             │
└──────────────────────────────────────────────────┘
```

- `core/` — pure logic (KB, classifier, sanitizer, mocks, prompts, patches), no MCP-specific code.
- `tools/` — thin orchestration layer wiring `core/` into MCP tool calls.
- `templates/` — markdown templates for the two persistent artifacts.
- `patches/` — pre-written refactor patches the demo applies.

## Running tests

```bash
pip install pytest
pytest -v
```

Tests cover: KB CRUD, classifier (regex + scan), Faker mock generation, sanitizer with scope filtering, patch loader, markdown templates.

## What's a "vibe coder"?

A non-technical founder who builds software with AI agents. They can describe a feature in plain English, but they don't know which env var to put a Stripe key in, why `.env` shouldn't be committed, or how to keep customer data away from a contractor. **VibeGuard guards them while they vibe-code.**

## Status

Hackathon MVP. The MCP server + 3 tools work end-to-end. The `patches/fe_be_split/` directory ships an empty placeholder manifest — to enable the live refactor demo, add real `.patch` files (git diff format) targeting your demo codebase.

## License

MIT
