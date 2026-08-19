"""Canonical schematic data model used by all format adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def key(self, digits: int = 6) -> tuple[float, float]:
        return (round(self.x, digits), round(self.y, digits))


@dataclass(slots=True)
class Pin:
    number: str
    name: str = ""
    electrical_type: str = ""
    position: Point | None = None
    net: str | None = None
    uuid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Component:
    reference: str
    value: str = ""
    lib_id: str = ""
    unit: int = 1
    position: Point | None = None
    rotation: float = 0.0
    properties: dict[str, str] = field(default_factory=dict)
    pins: list[Pin] = field(default_factory=list)
    uuid: str | None = None

    def pin(self, number: str) -> Pin | None:
        return next((pin for pin in self.pins if pin.number == str(number)), None)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Wire:
    start: Point
    end: Point
    uuid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Net:
    name: str
    pins: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    points: list[Point] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Schematic:
    name: str
    source: str
    format: str = "kicad"
    version: str = ""
    generator: str = ""
    components: list[Component] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def component(self, reference: str) -> Component | None:
        target = reference.upper()
        return next((c for c in self.components if c.reference.upper() == target), None)

    def net(self, name: str) -> Net | None:
        return next((net for net in self.nets if net.name == name), None)

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "format": self.format,
            "version": self.version,
            "generator": self.generator,
            "component_count": len(self.components),
            "net_count": len(self.nets),
            "wire_count": len(self.wires),
            "warnings": list(self.warnings),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "components": [component.to_dict() for component in self.components],
            "nets": [net.to_dict() for net in self.nets],
            "wires": [wire.to_dict() for wire in self.wires],
        }
