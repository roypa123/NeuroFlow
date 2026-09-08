"""Central secret redaction. See docs/15-security-and-credentials.md #15.6
item 2: "redaction at the sink, not at each call site, because per-call-
site discipline always fails eventually."

One `SecretRegistry` per execution. Every decrypted credential/secret-
variable string value gets registered once (in `run_execution.py`,
immediately after resolving credentials and `$vars`), and every log line,
error payload, and persisted item passes through `redact()`/`redact_json()`
before it can reach a database row, an SSE event, or an API response.
"""
from __future__ import annotations

from typing import Any

_REDACTED = "[REDACTED]"
_MIN_SECRET_LENGTH = 3  # a 1-2 char "secret" would redact half of English


class SecretRegistry:
    def __init__(self) -> None:
        self._secrets: set[str] = set()

    def register(self, value: str) -> None:
        if len(value) >= _MIN_SECRET_LENGTH:
            self._secrets.add(value)

    def register_many(self, values: Any) -> None:
        for value in values:
            if isinstance(value, str):
                self.register(value)

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            if secret in text:
                text = text.replace(secret, _REDACTED)
        return text

    def redact_json(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, dict):
            return {k: self.redact_json(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact_json(v) for v in value]
        return value
