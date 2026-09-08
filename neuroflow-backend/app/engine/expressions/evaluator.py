"""Tree-walking evaluator over the restricted AST from `parser.py`, plus
the `{{ }}` template resolution and per-parameter recursive resolution
that `app.engine.context` calls per item. See docs/12-execution-engine.md
#12.6: 100 ms CPU budget and a 1 MB result cap per expression.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.engine.expressions.errors import ExpressionError
from app.engine.expressions.parser import (
    Binary,
    Call,
    Ident,
    Index,
    Literal,
    Member,
    Node,
    ParseError,
    Ternary,
    Unary,
    parse,
)
from app.engine.expressions.scope import ExecutionScope
from app.engine.expressions.tokenizer import TokenizeError

MAX_STEPS = 20_000
MAX_DURATION_SECONDS = 0.1
MAX_RESULT_BYTES = 1_000_000

_EXPR_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)


class _Budget:
    __slots__ = ("steps", "deadline")

    def __init__(self) -> None:
        self.steps = 0
        self.deadline = time.monotonic() + MAX_DURATION_SECONDS

    def tick(self, expression: str) -> None:
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise ExpressionError(
                "Expression exceeded its step budget", expression=expression
            )
        if self.steps % 64 == 0 and time.monotonic() > self.deadline:
            raise ExpressionError(
                f"Expression exceeded the {MAX_DURATION_SECONDS * 1000:.0f} ms budget",
                expression=expression,
            )


def _resolve_member(obj: Any, name: str) -> Any:
    if name == "length" and isinstance(obj, list | str):
        return len(obj)
    if isinstance(obj, dict):
        return obj.get(name)
    if isinstance(obj, list):
        return None
    return getattr(obj, name, None)


def _resolve_index(obj: Any, key: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    if isinstance(obj, list):
        if isinstance(key, int | float):
            idx = int(key)
            return obj[idx] if -len(obj) <= idx < len(obj) else None
        return None
    if hasattr(obj, "__getitem__"):
        return obj[key]
    return None


def _truthy(value: Any) -> bool:
    return bool(value)


def _eval(node: Node, roots: dict[str, Any], budget: _Budget, expression: str) -> Any:
    budget.tick(expression)
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Ident):
        if node.name in roots:
            return roots[node.name]
        raise ExpressionError(f"Unknown identifier: {node.name}", expression=expression)
    if isinstance(node, Member):
        obj = _eval(node.obj, roots, budget, expression)
        return _resolve_member(obj, node.prop)
    if isinstance(node, Index):
        obj = _eval(node.obj, roots, budget, expression)
        key = _eval(node.index, roots, budget, expression)
        return _resolve_index(obj, key)
    if isinstance(node, Call):
        callee = _eval(node.callee, roots, budget, expression)
        if not callable(callee):
            raise ExpressionError(
                "Attempted to call a non-function value", expression=expression
            )
        args = [_eval(a, roots, budget, expression) for a in node.args]
        try:
            return callee(*args)
        except ExpressionError:
            raise
        except Exception as exc:  # noqa: BLE001 -- surfaced as a diagnosable expression error
            raise ExpressionError(str(exc), expression=expression) from exc
    if isinstance(node, Unary):
        operand = _eval(node.operand, roots, budget, expression)
        if node.op == "!":
            return not _truthy(operand)
        if node.op == "-":
            return -operand
    if isinstance(node, Binary):
        left = _eval(node.left, roots, budget, expression)
        if node.op == "&&":
            if not _truthy(left):
                return left
            return _eval(node.right, roots, budget, expression)
        if node.op == "||":
            if _truthy(left):
                return left
            return _eval(node.right, roots, budget, expression)
        right = _eval(node.right, roots, budget, expression)
        return _apply_binary(node.op, left, right, expression)
    if isinstance(node, Ternary):
        cond = _eval(node.cond, roots, budget, expression)
        branch = node.then if _truthy(cond) else node.orelse
        return _eval(branch, roots, budget, expression)
    raise ExpressionError(
        f"Unsupported expression node: {node!r}", expression=expression
    )


def _apply_binary(op: str, left: Any, right: Any, expression: str) -> Any:
    try:
        if op == "+":
            # JS-flavored: `+` with either side a string concatenates
            # (stringifying the other side) rather than raising, matching
            # docs/12-execution-engine.md #12.6's expression examples.
            if isinstance(left, str) or isinstance(right, str):
                return _stringify(left) + _stringify(right)
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "%":
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
    except TypeError as exc:
        raise ExpressionError(
            f"Cannot apply {op!r} to {left!r} and {right!r}", expression=expression
        ) from exc
    raise ExpressionError(f"Unknown operator: {op}", expression=expression)


def evaluate_expression(source: str, scope: ExecutionScope) -> Any:
    try:
        ast = parse(source)
    except (ParseError, TokenizeError) as exc:
        raise ExpressionError(
            str(exc), expression=source, scope=scope.diagnostic_snapshot()
        ) from exc
    try:
        return _eval(ast, scope.roots(), _Budget(), source)
    except ExpressionError as exc:
        if not exc.scope:
            exc.scope = scope.diagnostic_snapshot()
        raise


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict | list):
        return json.dumps(value)
    return str(value)


def _check_result_size(value: Any, *, expression: str) -> None:
    try:
        size = len(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return
    if size > MAX_RESULT_BYTES:
        raise ExpressionError(
            f"Expression result exceeds the {MAX_RESULT_BYTES} byte cap",
            expression=expression,
        )


def resolve_expression_string(raw: str, scope: ExecutionScope) -> Any:
    """A parameter value that starts with `=` is an expression. A single
    `{{ ... }}` spanning the whole (trimmed) string returns the evaluated
    value with its native type preserved; anything else is treated as a
    template and interpolated to a string."""
    if not raw.startswith("="):
        return raw
    body = raw[1:]
    matches = list(_EXPR_RE.finditer(body))
    if not matches:
        return body
    only_match = matches[0]
    if len(matches) == 1 and body.strip() == only_match.group(0).strip():
        value = evaluate_expression(only_match.group(1), scope)
        _check_result_size(value, expression=body)
        return value

    def _replace(match: re.Match[str]) -> str:
        return _stringify(evaluate_expression(match.group(1), scope))

    result = _EXPR_RE.sub(_replace, body)
    _check_result_size(result, expression=body)
    return result


def resolve_parameters(params: Any, scope: ExecutionScope) -> Any:
    if isinstance(params, str):
        return resolve_expression_string(params, scope)
    if isinstance(params, dict):
        return {key: resolve_parameters(value, scope) for key, value in params.items()}
    if isinstance(params, list):
        return [resolve_parameters(value, scope) for value in params]
    return params
