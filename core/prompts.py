"""Question templates for the 5-question handoff interview.

The MCP itself does NO LLM calls. Question generation is split:

- MCP returns these 5 templated questions, lightly customized with manifest
  data (e.g. "you have 12 secrets including Stripe and AWS").
- The host agent (Cursor / Claude Code) uses its own LLM (already paid for
  by the user's subscription) to ask the questions in chat, follow up,
  and interpret answers.

Optionally, a `skills/vibeguard-interview.skill.md` file ships with this
repo and tells the host agent how to orchestrate the full interview flow.
"""

# Static base — always returned by start_handoff.
BASE_QUESTIONS = [
    {
        "id": "persona_background",
        "category": "PERSONA",
        "question": "What's your technical background? (a) Non-technical — I describe features in plain English. (b) Some coding experience. (c) Experienced developer.",
        "expected_answer_format": "choice",
        "choices": ["a", "b", "c"],
    },
    {
        "id": "scope_directories",
        "category": "SCOPE",
        "question": "Which part of the codebase does the contractor need? (e.g. 'just the front-end', 'all of /app', 'specific feature folder')",
        "expected_answer_format": "open",
    },
    {
        "id": "advisory_fe_be",
        "category": "ADVISORY",
        "question": "PLACEHOLDER — see customize_questions below",
        "expected_answer_format": "yes_no",
    },
    {
        "id": "advisory_test_keys",
        "category": "ADVISORY",
        "question": "The contractor will need to test checkout flows. Want to give them a Stripe test-mode key (recommended), or block payment integration entirely from their scope?",
        "expected_answer_format": "choice",
        "choices": ["test-mode key", "block entirely"],
    },
    {
        "id": "workflow_delivery",
        "category": "SCOPE",
        "question": "After the contractor delivers, do you want to integrate their work manually, or have a guide for hooking it into your backend?",
        "expected_answer_format": "choice",
        "choices": ["manual", "guide me"],
    },
]


def customize_questions(summary: dict, intent: str) -> list[dict]:
    """Inject manifest-specific details into the FE/BE advisory question.

    This gives the questions concrete grounding in the user's actual codebase
    without needing an LLM call.
    """
    secrets_n = summary.get("SECRETS", {}).get("count", 0)
    pii_n = summary.get("PII", {}).get("count", 0)
    secret_kinds = sorted({i["kind"] for i in summary.get("SECRETS", {}).get("items", [])[:5]})
    pii_kinds = sorted({i["kind"] for i in summary.get("PII", {}).get("items", [])[:5]})

    secret_phrase = ", ".join(secret_kinds[:3]) if secret_kinds else "API keys"
    pii_phrase = ", ".join(pii_kinds[:3]) if pii_kinds else "customer data"

    advisory_fe_be_question = (
        f"I scanned your codebase and found {secrets_n} secret(s) "
        f"({secret_phrase}) and {pii_n} PII column(s) ({pii_phrase}). "
        f"Right now if you outsource without front-end / back-end separation, "
        f"the contractor's agent will see all of them. "
        f"**Want me to set up FE/BE separation so the contractor only sees a "
        f"mocked API?** This is the safer choice for privacy."
    )

    out = []
    for q in BASE_QUESTIONS:
        new_q = dict(q)
        if q["id"] == "advisory_fe_be":
            new_q["question"] = advisory_fe_be_question
        out.append(new_q)
    return out
