from core.advisories import applicable_advisories, ADVISORY_CATALOG


def test_fe_be_separation_applies_when_postgres_present():
    advs = applicable_advisories(["postgres_url", "openai_api_key"])
    by_id = {a["id"]: a for a in advs}
    assert by_id["fe_be_separation"]["current_status"] == "applicable"


def test_test_mode_keys_applies_when_stripe_present():
    advs = applicable_advisories(["stripe_secret_key"])
    by_id = {a["id"]: a for a in advs}
    assert by_id["test_mode_keys"]["current_status"] == "applicable"


def test_inapplicable_advisories_still_returned():
    # No stripe, no postgres — neither advisory should be applicable, but both
    # still returned so the skill can decide whether to mention them.
    advs = applicable_advisories(["openai_api_key"])
    statuses = {a["id"]: a["current_status"] for a in advs}
    assert statuses["fe_be_separation"] == "not_applicable"
    assert statuses["test_mode_keys"] == "not_applicable"


def test_catalog_entries_have_required_fields():
    for adv in ADVISORY_CATALOG:
        assert "id" in adv
        assert "label" in adv
        assert "summary" in adv
        assert "applies_when_keywords" in adv
