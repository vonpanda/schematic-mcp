"""Small dependency-free S-expression reader for KiCad text formats."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

SExpr: TypeAlias = str | list["SExpr"]


class SExprError(ValueError):
    """Raised when an S-expression document is malformed."""


@dataclass(slots=True)
class _Reader:
    text: str
    index: int = 0

    def _skip_space(self) -> None:
        length = len(self.text)
        while self.index < length:
            char = self.text[self.index]
            if char.isspace():
                self.index += 1
                continue
            # KiCad-generated files normally contain no comments, but supporting
            # semicolon comments makes fixtures and third-party exports friendlier.
            if char == ";":
                while self.index < length and self.text[self.index] not in "\r\n":
                    self.index += 1
                continue
            break

    def _string(self) -> str:
        self.index += 1
        out: list[str] = []
        length = len(self.text)
        while self.index < length:
            char = self.text[self.index]
            self.index += 1
            if char == '"':
                return "".join(out)
            if char == "\\":
                if self.index >= length:
                    raise SExprError("unterminated escape sequence")
                escaped = self.text[self.index]
                self.index += 1
                out.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
            else:
                out.append(char)
        raise SExprError("unterminated quoted string")

    def _atom(self) -> str:
        start = self.index
        length = len(self.text)
        while self.index < length:
            char = self.text[self.index]
            if char.isspace() or char in "();":
                break
            self.index += 1
        if start == self.index:
            raise SExprError(f"unexpected character at offset {self.index}")
        return self.text[start : self.index]

    def expression(self) -> SExpr:
        self._skip_space()
        if self.index >= len(self.text):
            raise SExprError("unexpected end of document")
        char = self.text[self.index]
        if char == '"':
            return self._string()
        if char != "(":
            return self._atom()

        self.index += 1
        result: list[SExpr] = []
        while True:
            self._skip_space()
            if self.index >= len(self.text):
                raise SExprError("unterminated list")
            if self.text[self.index] == ")":
                self.index += 1
                return result
            result.append(self.expression())


def parse(text: str) -> SExpr:
    """Parse exactly one S-expression from *text*."""
    reader = _Reader(text)
    value = reader.expression()
    reader._skip_space()
    if reader.index != len(text):
        raise SExprError(f"trailing content at offset {reader.index}")
    return value


def head(node: SExpr) -> str | None:
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return None


def children(node: SExpr, token: str) -> list[list[SExpr]]:
    if not isinstance(node, list):
        return []
    return [child for child in node[1:] if isinstance(child, list) and head(child) == token]


def child(node: SExpr, token: str) -> list[SExpr] | None:
    matches = children(node, token)
    return matches[0] if matches else None


def atom(node: SExpr, token: str, default: str = "") -> str:
    match = child(node, token)
    if match and len(match) > 1 and isinstance(match[1], str):
        return match[1]
    return default
