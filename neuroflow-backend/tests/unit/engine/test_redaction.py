"""The secret-leak sentinel: a registered secret value must never survive
`redact`/`redact_json`, in any position (top-level string, nested dict,
nested list, or substring of a longer string). See docs/15-security-and-
credentials.md #15.6 and this phase's plan's exit criterion.
"""

from __future__ import annotations

from app.engine.redaction import SecretRegistry

SENTINEL = "sk-live-SENTINEL-9f8a7b6c"


def test_redacts_an_exact_string_match() -> None:
    registry = SecretRegistry()
    registry.register(SENTINEL)

    assert registry.redact(SENTINEL) == "[REDACTED]"


def test_redacts_a_secret_embedded_in_a_longer_message() -> None:
    registry = SecretRegistry()
    registry.register(SENTINEL)

    message = f"Authorization: Bearer {SENTINEL} rejected with 401"

    assert SENTINEL not in registry.redact(message)
    assert "[REDACTED]" in registry.redact(message)


def test_redact_json_walks_nested_dicts_and_lists() -> None:
    registry = SecretRegistry()
    registry.register(SENTINEL)

    payload = {
        "statusCode": 401,
        "body": {"error": f"invalid token {SENTINEL}"},
        "history": [f"tried {SENTINEL}", "tried something else"],
    }

    redacted = registry.redact_json(payload)

    assert SENTINEL not in str(redacted)
    assert redacted["body"]["error"] == "invalid token [REDACTED]"
    assert redacted["history"][0] == "tried [REDACTED]"
    assert redacted["history"][1] == "tried something else"


def test_unregistered_values_pass_through_untouched() -> None:
    registry = SecretRegistry()
    registry.register(SENTINEL)

    assert registry.redact("nothing secret here") == "nothing secret here"


def test_very_short_values_are_never_registered() -> None:
    # A 1-2 char "secret" would redact half of English -- see
    # SecretRegistry's _MIN_SECRET_LENGTH.
    registry = SecretRegistry()
    registry.register("a")

    assert registry.redact("a cat sat on a mat") == "a cat sat on a mat"
