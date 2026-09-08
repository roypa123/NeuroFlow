"""Pratt parser producing a restricted AST -- literals, `$`-prefixed scope
identifiers, member/index access, whitelisted calls, arithmetic/comparison/
logical operators, and ternary. No arbitrary function definitions, no
loops/comprehensions, no attribute access to dunder names. See
docs/12-execution-engine.md #12.6 and ADR-010.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.expressions.tokenizer import Token, tokenize


class ParseError(ValueError):
    pass


class Node:
    __slots__ = ()


@dataclass(slots=True)
class Literal(Node):
    value: Any


@dataclass(slots=True)
class Ident(Node):
    name: str


@dataclass(slots=True)
class Member(Node):
    obj: Node
    prop: str


@dataclass(slots=True)
class Index(Node):
    obj: Node
    index: Node


@dataclass(slots=True)
class Call(Node):
    callee: Node
    args: list[Node]


@dataclass(slots=True)
class Unary(Node):
    op: str
    operand: Node


@dataclass(slots=True)
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass(slots=True)
class Ternary(Node):
    cond: Node
    then: Node
    orelse: Node


_LOGICAL_OR = ("||",)
_LOGICAL_AND = ("&&",)
_EQUALITY = ("==", "!=")
_RELATIONAL = ("<", "<=", ">", ">=")
_ADDITIVE = ("+", "-")
_MULTIPLICATIVE = ("*", "/", "%")


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _expect_punct(self, value: str) -> Token:
        token = self._peek()
        if token.kind != "PUNCT" or token.value != value:
            raise ParseError(f"Expected {value!r} at position {token.position}")
        return self._advance()

    def parse(self) -> Node:
        node = self._ternary()
        if self._peek().kind != "EOF":
            raise ParseError(f"Unexpected token at position {self._peek().position}")
        return node

    def _ternary(self) -> Node:
        cond = self._logical_or()
        if self._peek().kind == "PUNCT" and self._peek().value == "?":
            self._advance()
            then = self._ternary()
            self._expect_punct(":")
            orelse = self._ternary()
            return Ternary(cond, then, orelse)
        return cond

    def _binary_level(self, next_level: Any, ops: tuple[str, ...]) -> Node:
        left = next_level()
        while self._peek().kind == "PUNCT" and self._peek().value in ops:
            op = self._advance().value
            right = next_level()
            left = Binary(op, left, right)
        return left

    def _logical_or(self) -> Node:
        return self._binary_level(self._logical_and, _LOGICAL_OR)

    def _logical_and(self) -> Node:
        return self._binary_level(self._equality, _LOGICAL_AND)

    def _equality(self) -> Node:
        return self._binary_level(self._relational, _EQUALITY)

    def _relational(self) -> Node:
        return self._binary_level(self._additive, _RELATIONAL)

    def _additive(self) -> Node:
        return self._binary_level(self._multiplicative, _ADDITIVE)

    def _multiplicative(self) -> Node:
        return self._binary_level(self._unary, _MULTIPLICATIVE)

    def _unary(self) -> Node:
        token = self._peek()
        if token.kind == "PUNCT" and token.value in ("!", "-"):
            self._advance()
            return Unary(token.value, self._unary())
        return self._postfix()

    def _postfix(self) -> Node:
        node = self._primary()
        while True:
            token = self._peek()
            if token.kind == "PUNCT" and token.value == ".":
                self._advance()
                prop_token = self._advance()
                if prop_token.kind != "IDENT":
                    raise ParseError(f"Expected property name at {prop_token.position}")
                if prop_token.value.startswith("__") and prop_token.value.endswith("__"):
                    raise ParseError("Access to dunder attributes is not allowed")
                node = Member(node, prop_token.value)
            elif token.kind == "PUNCT" and token.value == "[":
                self._advance()
                index_expr = self._ternary()
                self._expect_punct("]")
                node = Index(node, index_expr)
            elif token.kind == "PUNCT" and token.value == "(":
                self._advance()
                args: list[Node] = []
                if not (self._peek().kind == "PUNCT" and self._peek().value == ")"):
                    args.append(self._ternary())
                    while self._peek().kind == "PUNCT" and self._peek().value == ",":
                        self._advance()
                        args.append(self._ternary())
                self._expect_punct(")")
                node = Call(node, args)
            else:
                break
        return node

    def _primary(self) -> Node:
        token = self._peek()
        if token.kind == "NUMBER":
            self._advance()
            return Literal(float(token.value) if "." in token.value else int(token.value))
        if token.kind == "STRING":
            self._advance()
            return Literal(token.value)
        if token.kind == "IDENT":
            self._advance()
            if token.value == "true":
                return Literal(True)
            if token.value == "false":
                return Literal(False)
            if token.value == "null":
                return Literal(None)
            if token.value in ("import", "eval", "exec", "__import__"):
                raise ParseError(f"{token.value!r} is not a permitted identifier")
            return Ident(token.value)
        if token.kind == "PUNCT" and token.value == "(":
            self._advance()
            node = self._ternary()
            self._expect_punct(")")
            return node
        raise ParseError(f"Unexpected token at position {token.position}")


def parse(source: str) -> Node:
    return _Parser(tokenize(source)).parse()
