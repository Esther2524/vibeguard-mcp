# VibeGuard

> **VibeGuard stands guard at the perimeter of your codebase** — every collaborator (and their AI agent) gets a scoped, sanitized view; real secrets never cross the line.
>
> *Vibe freely. We guard the rest.*
>
> _See [Threat model](#threat-model) for the protection scope._
>
> Built for the **Cursor Hackathon — *"Build what agents want."***

## What it does

You're a small business owner. You used AI to build your web app — Stripe checkout, customer database, all of it. Now you need help. A **contractor** for a new feature. An **advisor** reviewing your architecture. A **friend** giving design feedback. The moment any of them touches your codebase, their AI agents get full access by default. The contractor's Cursor sees your Stripe live key. The advisor's Claude sees your customer database. **Your codebase has no boundaries.**

**VibeGuard sets them.** It's a **skill + MCP combo**:

| Component | Role | Where it lives |
|---|---|---|
| **Skill** (`skills/vibeguard-interview.skill.md`) | **Brain.** Decides what to ask, how to phrase it, how to interpret answers. Owns the user-facing conversation. | Loaded into your host agent (Cursor / Claude Code). |
| **MCP server** | **Toolbox.** Scans codebase, classifies items, sanitizes files, applies refactor patches. | This repo. |
| **Host agent's LLM** | **Voice.** Asks the questions, listens to answers, calls the tools. | Your existing Cursor / Claude Code subscription. |

**No `ANTHROPIC_API_KEY` needed.** No extra LLM bill. The MCP is intentionally LLM-free.

## Architecture · framework + pluggable backends

VibeGuard is an **orchestration framework**. The handoff lifecycle has three phases. Each is a swappable **slot** — the framework defines the contract, a backend does the work.

```
              ┌──────────────────────────────────────────────────┐
              │  VibeGuard skill + MCP — the orchestrator        │
              │  (owns conversation, lifecycle, brief artifacts) │
              └────────────────────┬─────────────────────────────┘
                                   │
            ┌──────────────────────┼─────────────────────────┐
            ▼                      ▼                         ▼
       ┌─────────┐           ┌──────────┐             ┌──────────┐
       │  INDEX  │           │   SCAN   │             │ SANITIZE │
       │ what's  │           │  what's  │             │ generate │
       │ in the  │           │sensitive │             │workspace │
       │codebase │           │          │             │ + brief  │
       └─────────┘           └──────────┘             └──────────┘
            │                      │                         │
       MVP default:           MVP default:              MVP default:
       file walker            10 regex                  Faker mocks
       + filename             patterns                  + git apply
       matching                                         + prebuilt
                                                        patches

       Production:            Production:               Production:
       🤝 Nia                 🤝 Greptile               (Nia for
       semantic               cross-repo +              schema-aware
       indexing               git-history               mocks; LLM
                              secret scan               for novel
                                                        refactors)
```

| Slot | What MVP ships | What sponsor takes over |
|---|---|---|
| **INDEX** | flat file walk + filename matching | 🤝 **Nia** — semantic codebase understanding |
| **SCAN** | 10 hardcoded secret-pattern regexes | 🤝 **Greptile** — cross-repo + git-history secret scan |
| **SANITIZE** | Faker mocks + `git apply` of prebuilt patches | (Nia for schema-aware mocks; LLM for novel refactors) |

The skill, the MCP tool surface, the markdown artifacts, and the contractor workspace structure don't change when a sponsor slots in.

## Demo · the shopify-store target

Demo codebase: **[ycecilia/shopify-store](https://github.com/ycecilia/shopify-store)** — a purposefully vibe-coded Shopify-style storefront (polished Lovable-built UI on intentionally messy backend) with hardcoded Stripe key, AWS credentials, Google service account, and admin password sitting in `src/lib/config.ts`.

**See it work in 30 seconds, no Cursor required:**

```bash
git clone https://github.com/Esther2524/vibeguard-mcp.git
cd vibeguard-mcp
python3 -m venv .venv && .venv/bin/pip install -e . pytest
./scripts/see_it.sh
```

The script clones shopify-store, runs the full handoff, and shows BEFORE / AFTER of every file VibeGuard touches.

Under the hood, the three tools fire in this order:

```
register_codebase("/path/to/shopify-store")
  ↳ INDEX:  file walker classifies ~70 files
  ↳ SCAN:   regex finds 5 secrets — Stripe sk_test (×2),
            AWS access key (×2), Google service account private key
  ↳ writes ~/.vibeguard/kb.json

start_handoff(intent="hand off the front-end to Sarah", contractor_id="sarah")
  ↳ surfaces advisories: [fe_be_separation, test_mode_keys]
  ↳ skill asks the owner ~5 plain-English questions

complete_handoff(approved_advisories=[...], confirm=False)   # preview
  ↳ returns plan: 4 files in owner repo will change, workspace will be at ~/...
  ↳ skill shows plan to user, waits for confirmation

complete_handoff(approved_advisories=[...], confirm=True)    # execute
  ↳ SANITIZE: applies 2 prebuilt patches (config-to-env + stripe-cleanup)
  ↳ writes ~/vibeguard-workspaces/sarah-<id>/ (mocked Stripe, no real .env)
  ↳ writes vibeguard-owner-memory.md + vibeguard-contractor-brief.md
```

## The 3 MCP tools

| Tool | What it does |
|---|---|
| `register_codebase(path)` | Walks the codebase, classifies items into `SECRETS` / `PII` / `BUSINESS_LOGIC` / `SAFE_TO_SHARE`, persists to `~/.vibeguard/kb.json`. |
| `start_handoff(intent, contractor_id)` | Returns the manifest summary + the list of privacy advisories applicable to *this* codebase. |
| `complete_handoff(workspace_id, approved_advisories, scope_globs, persona_summary, ..., confirm=False)` | **Two-phase:** with `confirm=False`, returns the plan. With `confirm=True`, applies refactor patches, generates the sanitized workspace, writes `vibeguard-owner-memory.md` and `vibeguard-contractor-brief.md`. Idempotent. |

## How a handoff actually flows

```
User: "I want to hand off the front-end to Sarah."
         │
         ▼
   Host agent (Cursor) reads the skill → orchestrates:
         │
         ├──► vibeguard.register_codebase("/path/to/shopify-store")
         │     ← {manifest_id, 5 secrets, 0 PII columns}
         │
         ├──► vibeguard.start_handoff(intent="...", contractor_id="sarah")
         │     ← {workspace_id, manifest_summary, available_advisories}
         │
         │  Now the host agent (using its own LLM + skill guidance)
         │  asks the user ~5 questions in plain English, e.g.:
         │
         │    "I scanned your codebase — your front-end has 5 hardcoded
         │     secrets in src/lib/config.ts. Sarah's AI would see all of
         │     them. Want me to refactor so they move to env vars?"  → "yes"
         │
         │  …4 more grounded questions…
         │
         ├──► vibeguard.complete_handoff(
         │         workspace_id=...,
         │         approved_advisories=["fe_be_separation", "test_mode_keys"],
         │         scope_globs=["src/**", "package.json"],
         │         persona_summary="non-technical merchant, plain English",
         │         confirm=False                          ← preview first
         │     )
         │     ← {plan: {will_modify_owner_codebase: [...], summary_for_user}}
         │
         │  Skill shows the plan in chat → "Ready to proceed?" → user: "yes"
         │
         ├──► vibeguard.complete_handoff(..., confirm=True)   ← now execute
         │     ← {executed: true, workspace_path, applied_changes, ...}
         │
         ▼
   "Workspace ready at ~/vibeguard-workspaces/sarah-abc123/.
    I refactored your codebase: [list]. Send Sarah this folder."
```

The 5 questions can be slightly different each run — the skill defines the *themes* (persona, scope, advisories, workflow); the host LLM picks the wording.

## Quick start (Cursor integration)

```bash
# 1. Install
git clone https://github.com/Esther2524/vibeguard-mcp.git
cd vibeguard-mcp
python3 -m venv .venv && .venv/bin/pip install -e .

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

# 4. Restart Cursor. In chat:
#    "I want to hand off the front-end to Sarah"
#       → host agent picks up the skill, asks ~5 questions one at a time,
#         then calls complete_handoff (preview), shows you the plan,
#         asks for confirmation, then executes.
```

## Helper scripts

```bash
./scripts/see_it.sh                   # interactive walkthrough — recommended for first run
./scripts/quickstart.sh               # reset all state (run before each demo / rehearsal)
./scripts/quickstart.sh prewarm       # reset + warm KB so live demo isn't cold
./scripts/quickstart.sh dry-run       # reset + run full flow without Cursor
python scripts/dry_run.py /path/to/repo   # same as dry-run, on any codebase
```

## Project layout

- `core/` — pure logic (KB, classifier, sanitizer, mocks, patches, advisory catalog), no MCP-specific code, no LLM.
- `tools/` — thin orchestration layer wiring `core/` into MCP tool calls.
- `templates/` — markdown templates for the two persistent artifacts.
- `patches/` — pre-written refactor patches per advisory_id.
- `skills/` — host-agent skill files. **The most important file in the repo.**
- `scripts/` — quickstart, dry-run, see-it walkthrough.

## Threat model

VibeGuard is designed for one specific protection scope. It's worth being explicit about what it does and does not do.

**In scope — accidental leakage by cooperative agents.** A contractor's AI agent helpfully reads `config.ts` looking for context, then echoes a Stripe key into a chat message or commits it. VibeGuard prevents this by ensuring the workspace simply does not contain that file: real secrets are mocked and scope-excluded paths are absent. The brief also names workspace + owner-repo absolute paths so a cooperative agent can recognize the boundary.

**Out of scope today — adversarial exfiltration.** An attacker (or a misaligned AI agent) with shell-level filesystem access can ignore the brief and read the owner's real codebase directly. The brief is honor-system text, not OS enforcement. Defending this surface needs one of: a Claude Code permission hook that blocks paths outside the workspace, a Docker / macOS App Sandbox wrapper, or a `chroot`-style restricted shell. These are on the roadmap.

If your threat model includes adversarial contractors, layer one of those mechanisms on top of VibeGuard — don't rely on the brief alone.

## License

MIT
