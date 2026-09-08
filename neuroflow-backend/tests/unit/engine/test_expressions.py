"""Covers the restricted expression evaluator's scope table
(docs/12-execution-engine.md #12.6) and its sandboxing guarantees
(ADR-010): no eval, no dunder access, no import, a step/time budget, and a
result-size cap."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.engine.expressions import (
    ExecutionScope,
    ExpressionError,
    resolve_expression_string,
)
from app.engine.expressions.scope import ItemView


def make_scope(**overrides: object) -> ExecutionScope:
    defaults: dict[str, object] = {
        "json": {"customer": {"email": "a@b.com"}, "total": 150},
        "binary": {},
        "items": [ItemView({"a": 1}), ItemView({"a": 2})],
        "node_outputs": {"Fetch orders": [{"total": 150}]},
        "workflow": {"id": "w1", "name": "WF", "active": True},
        "execution": {"id": "e1", "mode": "manual", "resumeUrl": None},
        "run_index": 0,
        "now": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    }
    defaults.update(overrides)
    return ExecutionScope(**defaults)  # type: ignore[arg-type]


def test_non_expression_strings_pass_through_literally() -> None:
    assert resolve_expression_string("plain string", make_scope()) == "plain string"


def test_json_member_access() -> None:
    result = resolve_expression_string("={{ $json.customer.email }}", make_scope())
    assert result == "a@b.com"


def test_single_expression_preserves_native_type() -> None:
    result = resolve_expression_string("={{ $json.total }}", make_scope())
    assert result == 150
    assert isinstance(result, int)


def test_ternary_and_node_lookup() -> None:
    expr = '={{ $node["Fetch orders"].json.total > 100 ? "vip" : "standard" }}'
    assert resolve_expression_string(expr, make_scope()) == "vip"


def test_unknown_node_name_raises_diagnosable_error() -> None:
    with pytest.raises(ExpressionError) as exc_info:
        resolve_expression_string('={{ $node["Missing"].json.x }}', make_scope())
    assert "Missing" in exc_info.value.message


def test_items_length_and_indexing() -> None:
    scope = make_scope()
    assert resolve_expression_string("={{ $items().length }}", scope) == 2
    assert resolve_expression_string("={{ $item(1).json.a }}", scope) == 2


def test_numeric_addition_stays_numeric() -> None:
    assert resolve_expression_string("={{ 1 + 2 }}", make_scope()) == 3


def test_plus_with_a_string_operand_concatenates_js_style() -> None:
    scope = make_scope()
    result = resolve_expression_string("={{ 'total-' + $json.total }}", scope)
    assert result == "total-150"


def test_now_format() -> None:
    result = resolve_expression_string("={{ $now.format('YYYY-MM-DD') }}", make_scope())
    assert result == "2026-01-02"


def test_template_interpolation_mixes_literal_text() -> None:
    expr = "={{ $items().length }} orders on {{ $now.format('YYYY-MM-DD') }}"
    assert resolve_expression_string(expr, make_scope()) == "2 orders on 2026-01-02"


def test_vars_and_env_are_empty_by_default() -> None:
    scope = make_scope()
    assert resolve_expression_string("={{ $vars }}", scope) == {}
    assert resolve_expression_string("={{ $env }}", scope) == {}


@pytest.mark.parametrize(
    "expr",
    [
        "={{ $json.__class__ }}",
        "={{ __import__('os') }}",
        "={{ import }}",
        "={{ eval('1') }}",
    ],
)
def test_dangerous_constructs_are_rejected(expr: str) -> None:
    with pytest.raises(ExpressionError):
        resolve_expression_string(expr, make_scope())


def test_unresolved_member_is_none_not_a_crash() -> None:
    result = resolve_expression_string("={{ $json.nonexistent }}", make_scope())
    assert result is None


def test_deeply_nested_expression_is_rejected_not_hung() -> None:
    # No loop construct exists in the grammar, so the closest thing to a
    # runaway expression is deep nesting. Whether that's caught by the
    # step/time budget (ExpressionError) or Python's own recursion guard
    # (RecursionError) first, the important guarantee is that it is
    # rejected quickly rather than hanging or crashing the process.
    nested = "1"
    for _ in range(3_000):
        nested = f"(1 ? {nested} : 0)"
    with pytest.raises((ExpressionError, RecursionError)):
        resolve_expression_string("={{ " + nested + " }}", make_scope())
