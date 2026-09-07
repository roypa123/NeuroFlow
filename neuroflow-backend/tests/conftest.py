"""Shared pytest fixtures.

No database or Redis fixtures yet -- those land with the first real domain
module in Phase 2 (docs/19-roadmap.md), via testcontainers per
docs/17-testing-strategy.md #17.4. Phase 1's tests are unit-level (no
external dependency) plus one integration test against /health, which by
design needs neither.
"""
from __future__ import annotations

import os

# Settings are validated at import time (docs/08-backend-architecture.md
# #8.8), so tests need a minimally valid environment before anything in
# app.core.config is imported. Set these before any app import happens.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault(
    "CREDENTIAL_MASTER_KEY", "dGVzdC1tYXN0ZXIta2V5LTMyLWJ5dGVzLWV4YWN0bHkh"
)
