"""Tokenizer for the restricted expression grammar inside `{{ ... }}`. See
docs/12-execution-engine.md #12.6 and ADR-010: expressions are parsed with a
restricted grammar, never `eval`-ed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TokenKind = Literal["NUMBER", "STRING", "IDENT", "PUNCT", "EOF"]

_MULTI_CHAR_PUNCT = ("==", "!=", "<=", ">=", "&&", "||")
_SINGLE_CHAR_PUNCT = set(".[](),+-*/%<>!?:")


@dataclass(slots=True, frozen=True)
class Token:
    kind: TokenKind
    value: str
    position: int


class TokenizeError(ValueError):
    pass


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "\"'":
            start = i
            quote = ch
            i += 1
            buf: list[str] = []
            while i < n and source[i] != quote:
                if source[i] == "\\" and i + 1 < n:
                    escape = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
                    buf.append(escape.get(source[i + 1], source[i + 1]))
                    i += 2
                else:
                    buf.append(source[i])
                    i += 1
            if i >= n:
                raise TokenizeError(f"Unterminated string literal at position {start}")
            i += 1  # closing quote
            tokens.append(Token("STRING", "".join(buf), start))
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            start = i
            while i < n and (source[i].isdigit() or source[i] == "."):
                i += 1
            tokens.append(Token("NUMBER", source[start:i], start))
            continue
        if ch.isalpha() or ch in "_$":
            start = i
            while i < n and (source[i].isalnum() or source[i] in "_$"):
                i += 1
            tokens.append(Token("IDENT", source[start:i], start))
            continue
        matched_multi = next(
            (p for p in _MULTI_CHAR_PUNCT if source.startswith(p, i)), None
        )
        if matched_multi:
            tokens.append(Token("PUNCT", matched_multi, i))
            i += len(matched_multi)
            continue
        if ch in _SINGLE_CHAR_PUNCT:
            tokens.append(Token("PUNCT", ch, i))
            i += 1
            continue
        raise TokenizeError(f"Unexpected character {ch!r} at position {i}")
    tokens.append(Token("EOF", "", n))
    return tokens
