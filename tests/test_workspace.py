from pathlib import Path

import pytest

from schematic_mcp.workspace import Workspace


def _workspace_with_root(root: Path) -> Workspace:
    workspace = Workspace()
    workspace.root = root.resolve()
    return workspace


def test_resolve_relative_path_inside_root(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    workspace = _workspace_with_root(root)

    resolved = workspace._resolve("boards/main.kicad_sch")

    assert resolved == (root / "boards" / "main.kicad_sch").resolve()


def test_rejects_parent_directory_escape(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    workspace = _workspace_with_root(root)

    with pytest.raises(PermissionError, match="outside SCHEMATIC_MCP_ROOT"):
        workspace._resolve("../outside.kicad_sch")


def test_rejects_absolute_path_outside_root(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.kicad_sch"
    workspace = _workspace_with_root(root)

    with pytest.raises(PermissionError, match="outside SCHEMATIC_MCP_ROOT"):
        workspace._resolve(str(outside))


def test_rejects_symlink_escape(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    workspace = _workspace_with_root(root)

    with pytest.raises(PermissionError, match="outside SCHEMATIC_MCP_ROOT"):
        workspace._resolve("linked/secret.kicad_sch")
