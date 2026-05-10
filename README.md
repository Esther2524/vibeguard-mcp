# VibeGuard

> **VibeGuard stands guard at the perimeter of your codebase** — every collaborator (and their AI agent) gets a scoped, sanitized view; real secrets never cross the line.
>
> *Vibe freely. We guard the rest.*
>
> Built for the **Cursor Hackathon — *"Build what agents want."***

## What it does

You're a small business owner. You used AI to build your web app — Stripe checkout, customer database, all of it. Now you need help. A **contractor** for a new feature. An **advisor** reviewing your architecture. A **friend** giving design feedback. The moment any of them touches your codebase, their AI agents get full access by default. The contractor's Cursor sees your Stripe live key. The advisor's Claude sees your customer database. **Your codebase has no boundaries.**

**VibeGuard sets them.** It's a **skill + MCP combo** where the skill is the brain.

| Component | Role | Where it lives |
|---|---|---|
| **Skill** (`skills/vibeguard-interview.skill.md`) | **Brain.** Decides when to ask what, how to phrase it, how to interpret answers. Owns the user-facing conversation. | Loaded into your host agent (Cursor / Claude Code). |
| **MCP server** | **Toolbox.** Scans codebase, classifies items, sanitizes files, applies refactor patches. Returns *structured data*, not questions. | This repo. |
| **Host agent's LLM** | **Voice.** Asks the questions, listens to answers. | Your existing Cursor / Claude Code subscription. |

**No `ANTHROPIC_API_KEY` needed.** No extra LLM bill. The MCP is intentionally LLM-free.

## The 3 MCP tools

| Tool | What it does |
|---|---|
| `register_codebase(path)` | Walks the codebase, classifies items into `SECRETS` / `PII` / `BUSINESS_LOGIC` / `SAFE_TO_SHARE`, persists to a JSON KB at `~/.vibeguard/kb.json`. |
| `start_handoff(intent, contractor_id)` | Returns the manifest summary + the list of privacy advisories applicable to *this* codebase (e.g. `fe_be_separation`, `test_mode_keys`). **Does not return questions** — the skill writes those itself. |
| `complete_handoff(workspace_id, approved_advisories, scope_globs, persona_summary, ...)` | Accepts structured input synthesized from the skill's interview. Applies hardcoded refactor patches for any approved advisory, generates a sanitized contractor workspace, writes `vibeguard-owner-memory.md` (owner-side) and `vibeguard-contractor-brief.md` (contractor-side). Idempotent. |

## How a handoff actually flows

```
User: "I want to hand off the front-end to Sarah."
         │
         ▼
   Host agent (Cursor) reads the skill → orchestrates:
         │
         ├──► vibeguard.register_codebase(...)
         │     ← {12 secrets, 4 PII columns}
         │
         ├──► vibeguard.start_handoff(intent="...", contractor_id="sarah")
         │     ← {workspace_id, manifest_summary, available_advisories}
         │
         │  Now the host agent (using its own LLM + skill guidance)
         │  asks the user 5 questions in plain English, e.g.:
         │
         │    "I scanned your codebase — your front-end queries the database
         │     directly. Sarah's AI would see real customer emails. Want me
         │     to refactor that so she only sees a mocked API?"  → user: "yes"
         │
         │  …4 more grounded questions…
         │
         ├──► vibeguard.complete_handoff(
         │         workspace_id=...,
         │         approved_advisories=["fe_be_separation", "test_mode_keys"],
         │         scope_globs=["app/**", "package.json"],
         │         persona_summary="non-technical merchant, plain English"
         │     )
         │     ← {workspace_path, applied_changes, mock_count, ...}
         │
         ▼
   "Workspace ready at ~/vibeguard-workspaces/sarah-abc123/.
    I refactored your codebase: [list]. Send Sarah this folder."
```

The 5 questions can be slightly different each run — that's fine and expected. The skill defines the *themes* (persona, scope, advisories, workflow). The host LLM picks the wording.

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
#                                            asks you ~5 questions one by one,
#                                            then calls complete_handoff
```

## Architecture

```
┌────────────────────────────────────────────────────────┐
│ Cursor / Claude Code (host)                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │ vibeguard-interview.skill.md ← THE BRAIN         │  │
│  │  - When to activate (trigger phrases)            │  │
│  │  - 5 question themes (persona / scope / advisory)│  │
│  │  - How to phrase questions for non-tech users    │  │
│  │  - How to map answers to structured input        │  │
│  │  - Privacy education tone guidelines             │  │
│  └──────────────────────────────────────────────────┘  │
│  ↑ Host's LLM reads the skill, asks questions,         │
│    calls MCP tools                                     │
└──────────┬─────────────────────────────────────────────┘
           │ MCP tool calls
           ▼
┌────────────────────────────────────────────────────────┐
│ VibeGuard MCP (Python, this repo) ← THE TOOLBOX        │
│  - register_codebase: scan + classify                  │
│  - start_handoff: return manifest + advisories         │
│  - complete_handoff: refactor + sanitize + artifacts   │
│  ↓                                                     │
│  CodebaseKB (JSON file at ~/.vibeguard/kb.json)        │
│  Patches (hardcoded git-diffs in patches/<advisory>/)  │
└────────────────────────────────────────────────────────┘
```

- `core/` — pure logic (KB, classifier, sanitizer, mocks, patches, advisory catalog), no MCP-specific code, no LLM.
- `tools/` — thin orchestration layer wiring `core/` into MCP tool calls.
- `templates/` — markdown templates for the two persistent artifacts.
- `patches/` — pre-written refactor patches per advisory_id.
- `skills/` — host-agent skill files. **This is the most important file in the repo.**

## Why split skill and MCP this way?

MCP is great for **mechanism** (file IO, regex scans, classifications, file copies, applying git patches) — deterministic, testable, language-neutral.

The skill is great for **policy + voice** (how to talk to a non-technical user, what to ask in what order, how to frame privacy education) — declarative markdown that the host's LLM can read and follow.

If we put question generation inside the MCP, we'd need:
- A second API key for the MCP's LLM
- A second LLM bill
- Less context (MCP doesn't see your full chat history; the host LLM does)
- Markdown editing wouldn't change behavior (Python deploy required)

Splitting them means:
- **Zero extra API keys**
- The host's LLM has full chat context to ask grounded follow-ups
- Editing the skill markdown changes behavior immediately (no MCP redeploy)
- The skill is the user-visible IP — easy to fork, customize, audit

## Running tests

```bash
pip install pytest
pytest -v
```

Tests cover: KB CRUD, classifier (regex + scan), Faker mock generation, sanitizer with scope filtering, patch loader, markdown templates, advisory applicability. All 36 pass.

## What's a "vibe coder"?

A non-technical founder who builds software with AI agents. They can describe a feature in plain English, but they don't know which env var to put a Stripe key in, why `.env` shouldn't be committed, or how to keep customer data away from a contractor. **VibeGuard guards them while they vibe-code.**

## Status

Hackathon MVP, v0.3.

- ✅ MCP server + 3 tools work end-to-end
- ✅ Skill orchestrates the full handoff
- ✅ 36/36 tests passing
- 🟡 `patches/fe_be_separation/` ships with placeholder manifest — to enable the live refactor demo, add real `.patch` files (git diff format) targeting your demo codebase

## License

MIT
