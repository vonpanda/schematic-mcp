import pytest

from schematic_mcp.sexpr import SExprError, child, loads, scalar, tag


def test_parse_basic_expression():
    root = loads('(root (name "hello world") (n 42))')
    assert tag(root) == "root"
    assert scalar(child(root, "name")) == "hello world"
    assert scalar(child(root, "n")) == "42"


def test_quoted_escapes_and_comments():
    root = loads('(root ; ignored\n (text "a\\\"b"))')
    assert scalar(child(root, "text")) == 'a"b'


def test_unbalanced_expression_fails():
    with pytest.raises(SExprError):
        loads("(root (x 1)")
