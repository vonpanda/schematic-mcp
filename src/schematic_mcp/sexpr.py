"""Small, dependency-free S-expression reader used for KiCad schematic files."""
from __future__ import annotations

from collections.abc import Iterator
from typing import TypeAlias

SExpr: TypeAlias = str | list["SExpr"]


class SExprError(ValueError):
    """Raised when an S-expression cannot be parsed."""


def _tokens(text: str) -> Iterator[str]:
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == ";":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch in "()":
            yield ch
            i += 1
            continue
        if ch == '"':
            i += 1
            out: list[str] = []
            while i < n:
                ch = text[i]
                if ch == '"':
                    i += 1
                    break
                if ch == "\\":
                    i += 1
                    if i >= n:
                        raise SExprError("unterminated escape sequence")
                    escaped = text[i]
                    out.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    i += 1
                    continue
                out.append(ch)
                i += 1
            else:
                raise SExprError("unterminated quoted string")
            yield "".join(out)
            continue
        start = i
        while i < n and not text[i].isspace() and text[i] not in "();":
            i += 1
        if start == i:
            raise SExprError(f"unexpected character at offset {i}")
        yield text[start:i]


def loads(text: str) -> SExpr:
    """Parse one top-level S-expression."""
    stack: list[list[SExpr]] = []
    roots: list[SExpr] = []
    for token in _tokens(text):
        if token == "(":
            node: list[SExpr] = []
            if stack:
                stack[-1].append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise SExprError("unexpected closing parenthesis")
            stack.pop()
        else:
            if not stack:
                roots.append(token)
            else:
                stack[-1].append(token)
    if stack:
        raise SExprError("unterminated list")
    if len(roots) != 1:
        raise SExprError(f"expected one root expression, found {len(roots)}")
    return roots[0]


def tag(node: SExpr) -> str | None:
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return None


def children(node: SExpr, name: str) -> list[list[SExpr]]:
    if not isinstance(node, list):
        return []
    return [item for item in node[1:] if isinstance(item, list) and tag(item) == name]


def child(node: SExpr, name: str) -> list[SExpr] | None:
    matches = children(node, name)
    return matches[0] if matches else None


def scalar(node: SExpr | None, index: int = 1, default: str | None = None) -> str | None:
    if not isinstance(node, list) or len(node) <= index or not isinstance(node[index], str):
        return default
    return node[index]


def walk(node: SExpr) -> Iterator[list[SExpr]]:
    if not isinstance(node, list):
        return
    yield node
    for item in node[1:]:
        if isinstance(item, list):
            yield from walk(item)
