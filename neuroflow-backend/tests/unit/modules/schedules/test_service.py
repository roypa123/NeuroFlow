"""Cron computation and the invalid-expression failure mode. See
docs/09-domain-modules.md #9.12."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.schedules.exceptions import InvalidCronExpressionError
from app.modules.schedules.service import compute_next_run


def test_hourly_cron_advances_to_the_next_hour_boundary() -> None:
    after = datetime(2026, 1, 1, 10, 30, tzinfo=UTC)

    next_run = compute_next_run("0 * * * *", after=after)

    assert next_run == datetime(2026, 1, 1, 11, 0, tzinfo=UTC)


def test_next_run_is_always_strictly_after_the_reference_time() -> None:
    after = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    next_run = compute_next_run("0 12 * * *", after=after)

    # Even though "at 12:00" matches `after` exactly, croniter returns the
    # *next* occurrence -- tomorrow, not right now -- or a schedule
    # created at its own fire time would immediately re-fire.
    assert next_run > after


def test_invalid_cron_expression_raises_a_typed_error() -> None:
    with pytest.raises(InvalidCronExpressionError):
        compute_next_run("not a cron expression", after=datetime.now(UTC))
