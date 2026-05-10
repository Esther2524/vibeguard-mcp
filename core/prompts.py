"""LLM prompt templates for the 5-question interview generator."""

INTERVIEW_SYSTEM = """You are a privacy-aware advisor helping a non-technical small business owner safely outsource code work to a contractor.

Generate exactly 5 clarifying questions in JSON format. Mix three categories:
- 1 PERSONA question (technical background, prior contractor experience)
- 1 SCOPE question (what files/data the contractor needs)
- 2 ADVISORY questions (architectural privacy improvements like FE/BE separation, mock test keys — explain WHY each matters in plain English the owner can understand)
- 1 SCOPE/workflow question (delivery / integration approach)

Return ONLY a JSON array, no other text. Each item is:
{
  "id": "string-like-persona_background",
  "category": "PERSONA" | "SCOPE" | "ADVISORY",
  "question": "the human-readable question, with educational context if ADVISORY",
  "expected_answer_format": "yes_no" | "open" | "choice",
  "choices": ["A", "B", "C"]
}

CRITICAL: At least one ADVISORY question MUST have id="advisory_fe_be" and ask about front-end/back-end separation. The owner needs to be able to answer "yes" to trigger our refactor."""


def interview_prompt(intent: str, manifest_summary: dict) -> str:
    secrets_count = manifest_summary.get("SECRETS", {}).get("count", 0)
    secrets_kinds = [i["kind"] for i in manifest_summary.get("SECRETS", {}).get("items", [])[:5]]
    pii_count = manifest_summary.get("PII", {}).get("count", 0)
    pii_kinds = [i["kind"] for i in manifest_summary.get("PII", {}).get("items", [])[:5]]
    return f"""Owner intent: "{intent}"

Codebase context (from KB):
- Secrets detected: {secrets_count} items including {secrets_kinds}
- PII columns: {pii_count} items including {pii_kinds}

Generate the 5 questions per the system instructions. Remember: include id="advisory_fe_be" for the FE/BE question."""


# Hardcoded fallback for when LLM is unavailable
FALLBACK_QUESTIONS = [
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
        "question": "Right now your front-end queries the database directly — that means the contractor's agent could see customer emails. Want me to set up front-end/back-end separation so the contractor only sees a mocked API? This is the safer choice for privacy.",
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
