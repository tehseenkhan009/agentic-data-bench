from src.guardrails import EXECUTION_POLICY, REVIEW_POLICY


def test_execution_policy_has_expected_allowed_imports():
    assert "pandas" in EXECUTION_POLICY.allowed_imports
    assert "os" not in EXECUTION_POLICY.allowed_imports


def test_execution_policy_bans_dangerous_tokens():
    for token in ("import os", "eval(", "exec(", "subprocess"):
        assert any(token in banned for banned in EXECUTION_POLICY.banned_tokens)


def test_review_policy_has_a_finite_retry_ceiling():
    assert REVIEW_POLICY.max_retries >= 1
    assert REVIEW_POLICY.max_retries <= 5  # sanity bound, not just "must be positive"
