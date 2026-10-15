"""Canonical schematic model exposed to MCP clients."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Pin:
    number: str
    name: str = ""
    electrical_type: str = ""
    position: tuple[float, float] | None = None
    net: str | None = None
    evidence: dict[str, Any] | None = None
    no_connect: bool = False


@dataclass(slots=True)
class Component:
    reference: str
    value: str
    lib_id: str
    unit: int = 1
    position: tuple[float, float] | None = None
    rotation: float = 0.0
    properties: dict[str, str] = field(default_factory=dict)
    pins: list[Pin] = field(default_factory=list)
    evidence: dict[str, Any] | None = None


@dataclass(slots=True)
class Net:
    name: str
    labels: list[str] = field(default_factory=list)
    pins: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class SheetRef:
    name: str
    file: str
    uuid: str | None = None


@dataclass(slots=True)
class Schematic:
    path: str
    format: str
    version: str | None = None
    generator: str | None = None
    components: list[Component] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)
    sheets: list[SheetRef] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def connectivity_status(self) -> str:
        return "unverified" if self.provenance.get("method") in {"llm_vision", "imported_json"} else "source_resolved"

    @property
    def name(self) -> str:
        return Path(self.path).stem

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "connectivity_status": self.connectivity_status, **asdict(self)}

    def summary(self) -> dict[str, Any]:
        connected_pins = sum(1 for c in self.components for p in c.pins if p.net)
        total_pins = sum(len(c.pins) for c in self.components)
        return {
            "name": self.name,
            "path": self.path,
            "format": self.format,
            "version": self.version,
            "generator": self.generator,
            "components": len(self.components),
            "nets": len(self.nets),
            "pins": total_pins,
            "connected_pins": connected_pins,
            "child_sheets": len(self.sheets),
            "warnings": self.warnings,
            "connectivity_status": self.connectivity_status,
            "provenance": self.provenance,
        }
