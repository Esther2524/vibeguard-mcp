import re
from core.faker_mocks import mock_for_secret, mock_for_pii
from tests._fixtures import FAKE_STRIPE_LIVE, FAKE_AWS_KEY


def test_stripe_mock_has_correct_prefix_and_length():
    mock = mock_for_secret("stripe_secret_key", FAKE_STRIPE_LIVE)
    assert mock.startswith("sk_mock_VIBEGUARD_")
    assert 20 <= len(mock) <= 60


def test_aws_mock_has_correct_prefix_and_length():
    mock = mock_for_secret("aws_access_key", FAKE_AWS_KEY)
    assert mock.startswith("AKIA")
    assert len(mock) == 20  # AWS access keys are 20 chars


def test_email_pii_looks_like_email():
    mock = mock_for_pii("email")
    assert re.match(r"[\w.\-]+@[\w.\-]+", mock)


def test_phone_pii_contains_digits():
    mock = mock_for_pii("phone")
    assert any(c.isdigit() for c in mock)


def test_unknown_kind_falls_back_to_generic():
    mock = mock_for_secret("never_seen_before", "some_value")
    assert mock.startswith("MOCK_VIBEGUARD_")


def test_same_real_value_gets_same_mock():
    """Determinism: stable across calls so patches apply correctly."""
    a = mock_for_secret("openai_api_key", "test_value_aaa")
    b = mock_for_secret("openai_api_key", "test_value_aaa")
    assert a == b


def test_different_real_values_get_different_mocks():
    a = mock_for_secret("openai_api_key", "test_value_aaa")
    b = mock_for_secret("openai_api_key", "test_value_bbb")
    assert a != b
