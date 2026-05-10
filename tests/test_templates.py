from templates.owner_memory import render_owner_memory
from templates.contractor_brief import render_contractor_brief


def test_owner_memory_renders_with_handoff():
    md = render_owner_memory(
        existing_md=None,
        persona="Non-technical merchant. Sells handmade soap.",
        codebase_facts={
            "stack": "Next.js + Stripe + Supabase",
            "sensitive_files": [".env", "db/customers.sql"],
        },
        new_handoff={
            "date": "2026-05-10",
            "contractor": "sarah",
            "feature": "checkout email receipt",
            "approved": ["FE/BE separation"],
            "workspace": "./vibeguard-workspaces/sarah-fe-001",
        },
    )
    assert "Owner profile" in md
    assert "sarah" in md.lower()
    assert "FE/BE separation" in md
    assert "Next.js" in md


def test_owner_memory_handles_no_sensitive_files():
    md = render_owner_memory(
        existing_md=None,
        persona="Some persona",
        codebase_facts={"stack": "Plain HTML", "sensitive_files": []},
        new_handoff={
            "date": "2026-05-10",
            "contractor": "alice",
            "feature": "build a page",
            "approved": [],
            "workspace": "./ws",
        },
    )
    assert "_none detected_" in md
    assert "alice" in md


def test_contractor_brief_renders():
    md = render_contractor_brief(
        contractor="sarah",
        feature="checkout email receipt",
        scope_globs=["src/frontend/**"],
        forbidden_files=["src/backend/**", ".env*"],
        mocks_summary="Stripe key, AWS key, customer email column all mocked.",
    )
    assert "sarah" in md.lower()
    assert "src/frontend" in md
    assert "src/backend" in md
    assert "Do NOT" in md
    assert "checkout email receipt" in md
