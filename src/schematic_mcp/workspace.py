"""Current schematic state and filesystem boundary handling."""
from __future__ import annotations

import os
import hashlib
from pathlib import Path

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.models import Schematic
from schematic_mcp.parsers import KiCadSchematicParser


class Workspace:
    def __init__(self) -> None:
        root = os.environ.get("SCHEMATIC_MCP_ROOT")
        self.root = Path(root).expanduser().resolve() if root else None
        self._state: tuple[Schematic, CircuitGraph] | None = None

    @property
    def schematic(self) -> Schematic | None:
        return self._state[0] if self._state else None

    @property
    def graph(self) -> CircuitGraph | None:
        return self._state[1] if self._state else None

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
        schematic.provenance = {"method": "native_parser", "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()}
        self._state = (schematic, CircuitGraph(schematic))
        return schematic

    def extract(self, path: str, pages: list[int] | None = None, client=None) -> Schematic:
        """Explicit remote extraction. Commit state only after all pages validate."""
        from schematic_mcp.llm import JSONClient, LLMConfig
        from schematic_mcp.parsers.vision import VisionSchematicParser

        candidate = self._resolve(path)
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        if candidate.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Vision input must be PDF, PNG, JPEG or WebP; use open_schematic for KiCad")
        schematic = VisionSchematicParser(client or JSONClient(LLMConfig.from_env())).parse(candidate, pages)
        graph = CircuitGraph(schematic)
        self._state = (schematic, graph)
        return schematic

    def open_model(self, path: str) -> Schematic:
        from schematic_mcp.model_io import load_model
        candidate = self._resolve(path)
        if not candidate.is_file() or candidate.suffix.lower() != ".json":
            raise ValueError("Expected a canonical .json model file")
        schematic = load_model(candidate)
        self._state = (schematic, CircuitGraph(schematic))
        return schematic

    def require(self) -> tuple[Schematic, CircuitGraph]:
        state = self._state
        if state is None:
            raise RuntimeError("no schematic loaded; call open_schematic first")
        return state
