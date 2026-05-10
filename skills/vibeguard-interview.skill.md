---
name: vibeguard-interview
description: Orchestrates a privacy-aware contractor handoff for non-technical owners using the VibeGuard MCP. Trigger when the user wants to outsource part of their codebase ("hand off X to contractor", "outsource the front-end", "share my repo with someone for feature Y").
---

# VibeGuard Interview Skill

You are helping a **non-technical small business owner** safely outsource part of their codebase to a contractor. Use the **VibeGuard MCP** for the data + sanitization work; you handle the conversation.

## When to activate

Trigger phrases (in user's chat):
- "hand off the front-end / back-end / mobile / X to <name>"
- "outsource <feature> to <contractor>"
- "share my repo with <name> for <task>"
- "I'm hiring someone to build <feature>"

## The protocol (always 3 steps)

### Step 1 — Make sure the codebase is registered

Check if VibeGuard already has a manifest for the user's project. If unsure, just call:

```
vibeguard.register_codebase(codebase_path="<absolute path to user's project root>")
```

Returns `{manifest_id, zones: {SECRETS, PII, BUSINESS_LOGIC, SAFE_TO_SHARE}, warnings}`.

Show the user a quick summary: *"I scanned your codebase and found N secrets and M PII columns."*

### Step 2 — Get the 5-question template

```
vibeguard.start_handoff(intent="<exactly what the user said>", contractor_id="<contractor name or 'unknown'>")
```

Returns:
- `workspace_id` — keep this; you'll need it for step 3
- `questions` — list of 5 question objects, customized to the user's actual codebase
- `manifest_summary` — full secret/PII context for richer prompting

**Now run the interview yourself** — don't just dump the questions. For each question:

1. **Read the `question` field** — it's already plain English.
2. **Add educational warmth** for `category: "ADVISORY"` questions:
   - Explain WHY in 1 extra sentence using the manifest_summary data
   - "Specifically, your `customers.sql` has an `email` column — without separation that would be visible to the contractor"
3. **Be concrete** for `category: "SCOPE"` questions:
   - Offer 2-3 example answers if user seems unsure
4. **Be casual** for `category: "PERSONA"` questions:
   - Don't make it feel like a survey

**Wait for each answer before moving to the next.** Don't list all 5 at once.

### Step 3 — Synthesize the handoff

Once you have all 5 answers, call:

```
vibeguard.complete_handoff(
  workspace_id="<from step 2>",
  answers=[
    {"question_id": "persona_background", "answer": "<their reply>"},
    {"question_id": "scope_directories",  "answer": "<their reply>"},
    {"question_id": "advisory_fe_be",     "answer": "yes" | "no"},
    {"question_id": "advisory_test_keys", "answer": "test-mode key" | "block entirely"},
    {"question_id": "workflow_delivery",  "answer": "manual" | "guide me"},
  ]
)
```

Returns `{workspace_path, contractor_brief_path, owner_memory_path, applied_changes, mock_count, redaction_count, files_in_workspace}`.

### Step 4 — Report what you did

Show the user:
- ✅ "Workspace ready at `<workspace_path>`. Send this to your contractor."
- ✅ "I refactored your codebase: <list applied_changes>" (only if `applied_changes` is non-empty)
- ✅ "Saved a memory file at `<owner_memory_path>` so I'll remember this handoff next time."
- ✅ "Your contractor's AI agent will read `<contractor_brief_path>` and follow these rules: <summarize>"

## Privacy education tone

The user is **non-technical**. When you mention secrets / PII / refactors, always frame the WHY in plain English:

- ❌ "FE/BE separation prevents direct DB access from React components"
- ✅ "Right now your shopping page fetches customer data directly. If we keep it that way, your contractor's AI would see real customer emails. Splitting it means they only see fake data instead."

- ❌ "Stripe webhook signature verification needed"
- ✅ "Stripe needs to know the webhook actually came from them. Without verification, anyone could send fake payment confirmations."

## Idempotency

If the user changes their mind ("actually, also restrict X"), just call `complete_handoff` again with the **same workspace_id** and updated answers. The contractor brief gets overwritten in place; the contractor's agent will pick up the new rules on next session.

## What you DO NOT do

- ❌ Do not call any LLM tool from inside VibeGuard. The MCP itself is LLM-free. You (the host agent) are the brain.
- ❌ Do not write to the contractor workspace yourself. `complete_handoff` does that.
- ❌ Do not modify `vibeguard-owner-memory.md` directly — it's auto-maintained.
- ❌ Do not mock or sanitize files yourself — pass everything through the MCP.

## Failure modes to handle gracefully

| If you see | Do this |
|---|---|
| `register_codebase` returns 0 secrets and 0 PII | Tell user: *"Looks clean! Outsourcing this should be safe even without VibeGuard, but I'll still set up a workspace for tidiness."* Continue. |
| `start_handoff` returns `error: No manifest found` | Call `register_codebase` first, then retry. |
| `complete_handoff` returns `applied_changes` with `kind: "REFACTOR_FAILED"` | Tell user the patches couldn't apply (their codebase may have drifted from the demo state). Workspace still gets generated. |
| User asks a follow-up question instead of answering | Pause the interview. Answer their question. Then resume: *"Anyway, back to my question 3 of 5: ..."* |

---

*This skill orchestrates the VibeGuard MCP — see https://github.com/Esther2524/vibeguard-mcp*
