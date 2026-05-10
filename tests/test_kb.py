import os
import tempfile
from core.kb import KB
from tests._fixtures import FAKE_STRIPE_LIVE


def _temp_path():
    f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    f.close()
    os.unlink(f.name)
    return f.name


def test_kb_creates_manifest_and_recalls_secrets():
    path = _temp_path()
    try:
        kb = KB(path)
        manifest_id = kb.create_manifest("/path/to/code")
        assert manifest_id is not None

        secrets = [
            {"file": ".env", "locator": "L1", "kind": "stripe_secret_key",
             "value": FAKE_STRIPE_LIVE, "confidence": 1.0},
        ]
        kb.add_secrets(manifest_id, secrets)
        recalled = kb.get_secrets(manifest_id)
        assert len(recalled) == 1
        assert recalled[0]["kind"] == "stripe_secret_key"
        assert recalled[0]["value"] == FAKE_STRIPE_LIVE

        # Persistence: a fresh KB instance sees the same data
        kb2 = KB(path)
        assert len(kb2.get_secrets(manifest_id)) == 1
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_kb_adds_and_retrieves_pii():
    path = _temp_path()
    try:
        kb = KB(path)
        m = kb.create_manifest("/code")
        kb.add_pii(m, [{"file": "schema.sql", "locator": "L3:email", "kind": "email"}])
        pii = kb.get_pii(m)
        assert len(pii) == 1
        assert pii[0]["kind"] == "email"
    finally:
        os.unlink(path)


def test_set_mock_updates_value():
    path = _temp_path()
    try:
        kb = KB(path)
        m = kb.create_manifest("/code")
        kb.add_secrets(m, [{"file": ".env", "locator": "L1",
                            "kind": "stripe_secret_key", "value": FAKE_STRIPE_LIVE}])
        kb.set_mock_for(m, FAKE_STRIPE_LIVE, "sk_mock_VIBEGUARD_xxx")
        assert kb.get_secrets(m)[0]["mock_value"] == "sk_mock_VIBEGUARD_xxx"
    finally:
        os.unlink(path)


def test_handoff_lifecycle():
    path = _temp_path()
    try:
        kb = KB(path)
        m = kb.create_manifest("/code")
        hid = kb.create_handoff(m, "sarah", "front-end handoff")
        h = kb.get_handoff(hid)
        assert h["contractor_id"] == "sarah"
        assert h["workspace_path"] is None

        kb.save_handoff_answers(hid, '[{"q":"a"}]', "/tmp/workspace")
        h2 = kb.get_handoff(hid)
        assert h2["workspace_path"] == "/tmp/workspace"
        assert h2["answers_json"] == '[{"q":"a"}]'
    finally:
        os.unlink(path)


def test_latest_manifest_id_returns_most_recent():
    import time
    path = _temp_path()
    try:
        kb = KB(path)
        assert kb.latest_manifest_id() is None
        m1 = kb.create_manifest("/code1")
        time.sleep(0.01)
        m2 = kb.create_manifest("/code2")
        assert kb.latest_manifest_id() == m2
    finally:
        os.unlink(path)
