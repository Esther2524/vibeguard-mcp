"""Shape-preserving mock value generation for secrets + PII.

Mocks are deterministic per (kind, real_value) pair so patches that
substitute mock values are stable across runs.
"""
import hashlib
from faker import Faker

fake = Faker()
Faker.seed(42)  # deterministic for demo

_secret_cache: dict[tuple[str, str], str] = {}

SECRET_TEMPLATES = {
    "stripe_secret_key":  lambda h: f"sk_mock_VIBEGUARD_{h[:20]}",
    "stripe_test_key":    lambda h: f"sk_test_VIBEGUARD_{h[:20]}",
    "aws_access_key":     lambda h: f"AKIA{h[:16].upper()}",
    "openai_api_key":     lambda h: f"sk-mock-VIBEGUARD-{h[:24]}",
    "anthropic_key":      lambda h: f"sk-ant-mock-VIBEGUARD-{h[:24]}",
    "github_pat":         lambda h: f"ghp_VIBEGUARD_{h[:24]}",
    "postgres_url":       lambda h: "postgres://mock_user:mock_pass@localhost:5432/mock_db",
    "generic_jwt":        lambda h: f"eyJmock.eyJ{h[:32]}.signature_mock",
    "private_key_pem":    lambda h: f"-----BEGIN MOCK PRIVATE KEY-----\n[redacted by VibeGuard]\n-----END MOCK PRIVATE KEY-----",
    "slack_token":        lambda h: f"xoxb-mock-VIBEGUARD-{h[:20]}",
}

PII_GENERATORS = {
    "email":          lambda: fake.email(),
    "phone":          lambda: fake.phone_number(),
    "ssn":            lambda: fake.ssn(),
    "address":        lambda: fake.address().replace("\n", ", "),
    "name":           lambda: fake.name(),
    "first_name":     lambda: fake.first_name(),
    "last_name":      lambda: fake.last_name(),
    "dob":            lambda: fake.date_of_birth().isoformat(),
    "date_of_birth":  lambda: fake.date_of_birth().isoformat(),
    "credit_card":    lambda: fake.credit_card_number(),
    "creditcard":     lambda: fake.credit_card_number(),
    "card_number":    lambda: fake.credit_card_number(),
    "passport":       lambda: fake.passport_number() if hasattr(fake, "passport_number") else "MOCK_PASSPORT_001",
    "driver_license": lambda: f"MOCK_DL_{fake.random_int(10000, 99999)}",
    "tax_id":         lambda: f"MOCK_TAX_{fake.random_int(100000, 999999)}",
}


def mock_for_secret(kind: str, real_value: str) -> str:
    """Deterministic mock for a real secret value, shape-preserving when possible."""
    key = (kind, real_value)
    if key in _secret_cache:
        return _secret_cache[key]
    h = hashlib.sha256(real_value.encode()).hexdigest()
    template = SECRET_TEMPLATES.get(kind, lambda h: f"MOCK_VIBEGUARD_{h[:24]}")
    mock = template(h)
    _secret_cache[key] = mock
    return mock


def mock_for_pii(kind: str) -> str:
    """Realistic fake PII value (uses Faker's seeded RNG, so reproducible)."""
    gen = PII_GENERATORS.get(kind, lambda: fake.word())
    return gen()
