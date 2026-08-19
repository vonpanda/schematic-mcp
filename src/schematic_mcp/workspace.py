"""Current schematic state and filesystem boundary handling."""
from __future__ import annotations

import os
from pathlib import Path

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.models import Schematic
from schematic_mcp.parsers import KiCadSchematicParser


class Workspace:
    def __init__(self) -> None:
        root = os.environ.get("SCHEMATIC_MCP_ROOT")
        self.root = Path(root).expanduser().resolve() if root else None
        self.schematic: Schematic | None = None
        self.graph: CircuitGraph | None = None

    def _resolve(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute() and self.root:
            candidate = self.root / candidate
        candidate = candidate.resolve()
        if self.root and candidate != self.root and self.root not in candidate.parents:
            raise PermissionError(f"path is outside SCHEMATIC_MCP_ROOT ({self.root})")
        return candidate

    def open(self, path: str) -> Schematic:
        candidate = self._resolve(path)
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        if candidate.suffix.lower() != ".kicad_sch":
            raise ValueError("V0.1 currently supports .kicad_sch files only")
        schematic = KiCadSchematicParser().parse(candidate)
        self.schematic = schematic
        self.graph = CircuitGraph(schematic)
        return schematic

    def require(self) -> tuple[Schematic, CircuitGraph]:
        if self.schematic is None or self.graph is None:
            raise RuntimeError("no schematic loaded; call open_schematic first")
        return self.schematic, self.graph
