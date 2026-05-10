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
            "Refactor the codebase so the front-end calls a back-end API "
            "instead of touching the database directly. The contractor's "
            "agent then only sees a mocked API surface, never raw customer "
            "data or DB credentials."
        ),
        "applies_when_keywords": ["postgres_url"],
        # If the codebase has secrets that scream "DB connection in client code",
        # this advisory is applicable.
    },
    {
        "id": "test_mode_keys",
        "label": "Use test-mode keys for the contractor",
        "summary": (
            "Substitute live Stripe / payment keys with test-mode equivalents "
            "in the contractor workspace. The contractor can run real-looking "
            "checkout flows without touching real money."
        ),
        "applies_when_keywords": ["stripe_secret_key"],
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
