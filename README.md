# VibeGuard

> **A Privacy Guardian for Vibe Coders.**
> An MCP server that lets non-technical founders safely hand off code to contractors —
> contractor's agent works against a sanitized twin of the codebase, real secrets never cross the line.
>
> Built for the **Cursor Hackathon — *"Build what agents want."***

## What it does

When a non-technical founder ("vibe coder") wants to outsource part of their codebase — typically front-end work — they face a hard choice: hand over the entire repo (the contractor's AI agent now has full access to everything), or spend an evening manually scrubbing secrets and PII out of a fork.

**VibeGuard** replaces both options with three callable MCP tools + a host-side skill.

| Component | Role | Where it runs |
|---|---|---|
| **MCP server** | Mechanism: scans, classifies, sanitizes, applies patches | This repo |
| **Skill file** (`skills/vibeguard-interview.skill.md`) | Policy: orchestrates the 5-question interview, frames privacy education | Loaded into your host agent (Cursor / Claude Code) |
| **Host agent's LLM** | Brain: asks questions, interprets answers | Your existing Cursor / Claude Code subscription |

This split means **no separate API key for VibeGuard** — your host agent's LLM does all the talking; we just provide tools and a skill telling it how to use them.

## The 3 MCP tools

| Tool | What it does |
|---|---|
| `register_codebase(path)` | Walks the codebase, classifies items into `SECRETS` / `PII` / `BUSINESS_LOGIC` / `SAFE_TO_SHARE`, persists to a JSON KB at `~/.vibeguard/kb.json`. |
| `start_handoff(intent, contractor_id)` | Returns 5 clarifying questions (mixing persona / scope / **privacy education**) — already customized with your codebase's actual secret + PII counts. **No LLM call.** |
| `complete_handoff(workspace_id, answers)` | If the owner approved any architectural advisory (e.g. FE/BE split), **applies a hardcoded refactor patch to the owner's real codebase**, generates a sanitized contractor workspace with shape-preserving mocks, writes `vibeguard-owner-memory.md` (owner-side) and `vibeguard-contractor-brief.md` (contractor-side). |

## Quick start

```bash
# 1. Set up
git clone https://github.com/Esther2524/vibeguard-mcp.git
cd vibeguard-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Wire MCP into Cursor — edit ~/.cursor/mcp.json
{
  "mcpServers": {
    "vibeguard": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}

# 3. Drop the skill into your host agent
#    Cursor:        cp skills/vibeguard-interview.skill.md ~/.cursor/rules/
#    Claude Code:   cp skills/vibeguard-interview.skill.md ~/.claude/skills/

# 4. Restart your host. In chat:
#    "call vibeguard's ping tool"          → "vibeguard alive"
#    "register_codebase on /path/to/repo"  → returns a manifest
#    "I want to hand off the front-end to Sarah"
#                                          → host agent picks up the skill,
#                                            asks you 5 questions one by one,
#                                            then calls complete_handoff
```

**No `ANTHROPIC_API_KEY` needed.** The host agent's LLM does the conversation; the MCP server is pure mechanism.

## Architecture

```
┌────────────────────────────────────────────────────┐
│ Cursor / Claude Code (host)                        │
│  ┌──────────────────────────────────────────────┐  │
│  │ vibeguard-interview.skill.md (drop in)       │  │
│  │  → tells the host LLM how to orchestrate     │  │
│  └──────────────────────────────────────────────┘  │
│  ↑ Host's LLM asks questions, calls tools          │
└──────────┬─────────────────────────────────────────┘
           │ MCP tool calls
           ▼
┌────────────────────────────────────────────────────┐
│ VibeGuard MCP (Python, this repo)                  │
│  - register_codebase: scan + classify              │
│  - start_handoff: return manifest + 5 questions    │
│  - complete_handoff: sanitize + apply patches      │
│  ↓                                                 │
│  CodebaseKB (JSON file at ~/.vibeguard/kb.json)    │
└────────────────────────────────────────────────────┘
```

- `core/` — pure logic (KB, classifier, sanitizer, mocks, prompts, patches), no MCP-specific code.
- `tools/` — thin orchestration layer wiring `core/` into MCP tool calls.
- `templates/` — markdown templates for the two persistent artifacts.
- `patches/` — pre-written refactor patches the demo applies.
- `skills/` — host-agent skill files that orchestrate the user-facing flow.

## Why split MCP and Skill?

MCP is great for **mechanism** (file IO, scans, classifications) — deterministic, testable, language-neutral.
Skills are great for **policy** (how to talk to a non-technical user, what to ask in what order, how to frame privacy education) — declarative markdown that the host's LLM can read.

Putting LLM calls inside the MCP would mean:
- A second API key to manage
- A second LLM bill to pay
- Less context (MCP doesn't see your full chat history)

Splitting them means:
- Zero extra API keys
- The host's LLM has full chat context to do better question framing
- Easy for users to customize the interview by editing the skill markdown

## Running tests

```bash
pip install pytest
pytest -v
```

Tests cover: KB CRUD, classifier (regex + scan), Faker mock generation, sanitizer with scope filtering, patch loader, markdown templates. All 32 pass.

## What's a "vibe coder"?

A non-technical founder who builds software with AI agents. They can describe a feature in plain English, but they don't know which env var to put a Stripe key in, why `.env` shouldn't be committed, or how to keep customer data away from a contractor. **VibeGuard guards them while they vibe-code.**

## Status

Hackathon MVP. The MCP server + 3 tools work end-to-end. The `patches/fe_be_split/` directory ships an empty placeholder manifest — to enable the live refactor demo, add real `.patch` files (git diff format) targeting your demo codebase.

## License

MIT
