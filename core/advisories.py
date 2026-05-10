"""Privacy improvement advisories that VibeGuard can offer.

The MCP exposes WHICH advisories are *applicable* to a given codebase
(based on what was detected) but does NOT decide whether to ask the
user about them — that's the host agent's job, guided by the skill.

When the user approves an advisory, complete_handoff matches it against
patches/<advisory_id>/manifest.json and applies the patches.
"""
from typing import Any

# Catalog of advisories. A future version could ship many more
# (e.g. "extract_admin_route", "rotate_committed_secrets", etc.).
ADVISORY_CATALOG: list[dict[str, Any]] = [
    {
        "id": "fe_be_separation",
        "label": "Front-end / Back-end separation",
        "summary": (
            "Pull hardcoded secrets out of source files into env vars; route "
            "any direct external calls (Stripe, AWS, etc.) through a server-side "
            "API. The contractor's agent then only sees the front-end + a mocked "
            "API surface, never the raw secrets."
        ),
        # Triggered by any secret living in source code — that's the smell that
        # says "FE and BE are tangled and need to be separated".
        "applies_when_keywords": [
            "stripe_secret_key", "stripe_test_key", "aws_access_key",
            "openai_api_key", "anthropic_key", "github_pat", "postgres_url",
            "private_key_pem", "slack_token", "generic_jwt",
        ],
    },
    {
        "id": "test_mode_keys",
        "label": "Use test-mode keys for the contractor",
        "summary": (
            "Substitute live Stripe / payment keys with test-mode equivalents "
            "in the contractor workspace. The contractor can run real-looking "
            "checkout flows without touching real money."
        ),
        "applies_when_keywords": ["stripe_secret_key", "stripe_test_key"],
    },
]


def applicable_advisories(secret_kinds: list[str]) -> list[dict]:
    """Return the subset of advisories that apply to a codebase containing
    these secret kinds. Caller passes in the list of detected secret kinds."""
    out: list[dict] = []
    kinds_set = set(secret_kinds)
    for adv in ADVISORY_CATALOG:
        if any(kw in kinds_set for kw in adv["applies_when_keywords"]):
            out.append({
                "id": adv["id"],
                "label": adv["label"],
                "summary": adv["summary"],
                "current_status": "applicable",
            })
    # Always include all even if not applicable, marked as such — lets the
    # skill decide whether to mention them. Keeps the API surface stable.
    seen = {a["id"] for a in out}
    for adv in ADVISORY_CATALOG:
        if adv["id"] not in seen:
            out.append({
                "id": adv["id"],
                "label": adv["label"],
                "summary": adv["summary"],
                "current_status": "not_applicable",
            })
    return out
