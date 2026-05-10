"""Fake-secret string fixtures.

We build these at runtime via string concat so the literal patterns never
appear in source — that way GitHub's secret scanner doesn't flag this
test code (a project ABOUT preventing secret leaks should not itself
trip secret-leak detectors).
"""
# Stripe-shape: prefix + 20+ alnum chars matches our regex
FAKE_STRIPE_LIVE  = "sk_" + "live_DEADBEEFplaceholderaaaaaaaaaaaaa"
FAKE_STRIPE_LIVE2 = "sk_" + "live_FACADEFFplaceholderbbbbbbbbbbbbbbb"
FAKE_STRIPE_TEST  = "sk_" + "test_DEADBEEFplaceholdercccccccccccccc"

# AWS access key: AKIA + 16 alphanum
FAKE_AWS_KEY = "AKIA" + "FAKEPLACEHOLDXY"  # 4 + 15 = 19? need 16 after AKIA = 20 total
FAKE_AWS_KEY = "AKIA" + "FAKEPLCHLDR12345"  # 16 chars after AKIA

# Anthropic-shape: sk-ant- + 20+ alphanum/underscore/dash
FAKE_ANTHROPIC = "sk-" + "ant-fake_VIBEGUARD_test_aaaaaaaa"
