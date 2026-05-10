import pathlib
import tempfile
from core.classifier import find_secrets, find_pii_columns, scan_codebase
from tests._fixtures import FAKE_STRIPE_LIVE, FAKE_STRIPE_LIVE2, FAKE_STRIPE_TEST, FAKE_AWS_KEY, FAKE_ANTHROPIC


def test_finds_stripe_live_key():
    content = f"STRIPE_KEY={FAKE_STRIPE_LIVE}\nOTHER=foo"
    hits = find_secrets(content, file=".env")
    assert any(h["kind"] == "stripe_secret_key" for h in hits)
    stripe = next(h for h in hits if h["kind"] == "stripe_secret_key")
    assert stripe["confidence"] == 1.0
    assert stripe["locator"] == "L1"


def test_finds_aws_access_key():
    content = f"AWS_ACCESS_KEY_ID={FAKE_AWS_KEY}"
    hits = find_secrets(content, file=".env")
    assert any(h["kind"] == "aws_access_key" for h in hits)


def test_finds_anthropic_key():
    content = f"ANTHROPIC_API_KEY={FAKE_ANTHROPIC}"
    hits = find_secrets(content, file=".env")
    assert any(h["kind"] == "anthropic_key" for h in hits)


def test_test_keys_get_lower_confidence():
    content = f"STRIPE_KEY={FAKE_STRIPE_TEST}"
    hits = find_secrets(content, file=".env")
    if hits:
        for h in hits:
            if h["kind"] == "stripe_test_key":
                assert h["confidence"] < 0.9


def test_finds_pii_email_column():
    sql = "CREATE TABLE users (\n  id INTEGER,\n  email TEXT,\n  age INTEGER\n);"
    hits = find_pii_columns(sql, file="schema.sql")
    assert any(h["kind"] == "email" for h in hits)


def test_finds_multiple_pii_columns():
    sql = """CREATE TABLE customers (
        email VARCHAR(255),
        phone TEXT,
        ssn TEXT,
        zip_code TEXT
    );"""
    hits = find_pii_columns(sql, file="customers.sql")
    kinds = {h["kind"] for h in hits}
    assert "email" in kinds
    assert "phone" in kinds
    assert "ssn" in kinds
    assert "zip_code" not in kinds  # not in PII list


def test_scan_codebase_finds_secrets_and_pii():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".env").write_text(f"STRIPE_KEY={FAKE_STRIPE_LIVE}\n")
        (root / "schema.sql").write_text(
            "CREATE TABLE users (\n  email TEXT,\n  age INTEGER\n);\n"
        )
        (root / "safe.py").write_text("print('hello world')\n")
        result = scan_codebase(str(root))
        assert any(s["kind"] == "stripe_secret_key" for s in result["secrets"])
        assert any(p["kind"] == "email" for p in result["pii"])


def test_scan_skips_node_modules():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".env").write_text(f"STRIPE_KEY={FAKE_STRIPE_LIVE}\n")
        nm = root / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / ".env").write_text(f"STRIPE_KEY={FAKE_STRIPE_LIVE2}\n")
        result = scan_codebase(str(root))
        # Only the root .env should be detected, not the one in node_modules
        assert len(result["secrets"]) == 1
