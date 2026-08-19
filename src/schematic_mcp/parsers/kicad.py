"""KiCad .kicad_sch parser -> canonical schematic model."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from schematic_mcp.models import Component, Net, Pin, Schematic, SheetRef
from schematic_mcp.parsers.base import SchematicParser
from schematic_mcp.sexpr import SExpr, child, children, loads, scalar, tag, walk

Point = tuple[float, float]
_EPS = 1e-4


def _float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _int(value: str | None, default: int = 1) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _point_from_at(node: SExpr | None) -> tuple[Point, float]:
    if not isinstance(node, list):
        return (0.0, 0.0), 0.0
    x = _float(scalar(node, 1))
    y = _float(scalar(node, 2))
    rotation = _float(scalar(node, 3))
    return (x, y), rotation


def _key(point: Point) -> Point:
    return (round(point[0], 4), round(point[1], 4))


def _point_on_segment(point: Point, a: Point, b: Point, eps: float = _EPS) -> bool:
    px, py = point
    ax, ay = a
    bx, by = b
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > eps * max(1.0, abs(bx - ax) + abs(by - ay)):
        return False
    return min(ax, bx) - eps <= px <= max(ax, bx) + eps and min(ay, by) - eps <= py <= max(ay, by) + eps


class _DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[Point, Point] = {}

    def add(self, item: Point) -> None:
        item = _key(item)
        self.parent.setdefault(item, item)

    def find(self, item: Point) -> Point:
        item = _key(item)
        self.add(item)
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a: Point, b: Point) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


@dataclass(slots=True)
class _LibPin:
    number: str
    name: str
    electrical_type: str
    position: Point


class KiCadSchematicParser(SchematicParser):
    """Parse modern KiCad S-expression schematic files (.kicad_sch)."""

    def parse(self, path: str | Path) -> Schematic:
        source = Path(path)
        root = loads(source.read_text(encoding="utf-8"))
        if tag(root) != "kicad_sch":
            raise ValueError(f"{source} is not a KiCad schematic")
        lib_pins = self._parse_library_pins(root)
        components = self._parse_components(root, lib_pins)
        nets, warnings = self._connectivity(root, components)
        return Schematic(path=str(source.resolve()), format="kicad_sch", version=scalar(child(root, "version")), generator=scalar(child(root, "generator")), components=components, nets=nets, sheets=self._parse_sheets(root), warnings=warnings)

    def _parse_library_pins(self, root: SExpr) -> dict[str, list[_LibPin]]:
        result: dict[str, list[_LibPin]] = {}
        libs = child(root, "lib_symbols")
        if not isinstance(libs, list):
            return result
        for symbol in children(libs, "symbol"):
            lib_id = scalar(symbol) or ""
            pins: list[_LibPin] = []
            seen: set[tuple[str, Point]] = set()
            for node in walk(symbol):
                if tag(node) != "pin":
                    continue
                number = scalar(child(node, "number")) or ""
                name = scalar(child(node, "name")) or ""
                pos, _ = _point_from_at(child(node, "at"))
                identity = (number, _key(pos))
                if number and identity not in seen:
                    pins.append(_LibPin(number, name, scalar(node) or "", pos))
                    seen.add(identity)
            result[lib_id] = pins
        return result

    def _parse_components(self, root: SExpr, lib_pins: dict[str, list[_LibPin]]) -> list[Component]:
        components: list[Component] = []
        for symbol in children(root, "symbol"):
            lib_id = scalar(child(symbol, "lib_id")) or ""
            if not lib_id:
                continue
            position, rotation = _point_from_at(child(symbol, "at"))
            properties: dict[str, str] = {}
            for prop in children(symbol, "property"):
                name, value = scalar(prop, 1), scalar(prop, 2)
                if name is not None and value is not None:
                    properties[name] = value
            mirror_node = child(symbol, "mirror")
            mirror_axis = scalar(mirror_node) if mirror_node else None
            pins = [Pin(number=p.number, name=p.name, electrical_type=p.electrical_type, position=self._transform(p.position, position, rotation, mirror_axis)) for p in lib_pins.get(lib_id, [])]
            components.append(Component(reference=properties.get("Reference", "?"), value=properties.get("Value", lib_id.split(":")[-1]), lib_id=lib_id, unit=_int(scalar(child(symbol, "unit")), 1), position=position, rotation=rotation, properties=properties, pins=pins))
        return components

    @staticmethod
    def _transform(local: Point, origin: Point, rotation: float, mirror_axis: str | None) -> Point:
        x, y = local
        if mirror_axis == "x":
            y = -y
        elif mirror_axis == "y":
            x = -x
        angle = math.radians(rotation)
        return _key((origin[0] + x * math.cos(angle) - y * math.sin(angle), origin[1] + x * math.sin(angle) + y * math.cos(angle)))

    def _parse_sheets(self, root: SExpr) -> list[SheetRef]:
        result: list[SheetRef] = []
        for sheet in children(root, "sheet"):
            properties: dict[str, str] = {}
            for prop in children(sheet, "property"):
                name, value = scalar(prop, 1), scalar(prop, 2)
                if name and value is not None:
                    properties[name] = value
            name = properties.get("Sheetname", properties.get("Sheet Name", ""))
            filename = properties.get("Sheetfile", properties.get("Sheet File", ""))
            if name or filename:
                result.append(SheetRef(name=name, file=filename, uuid=scalar(child(sheet, "uuid"))))
        return result

    def _connectivity(self, root: SExpr, components: list[Component]) -> tuple[list[Net], list[str]]:
        ds = _DisjointSet()
        segments: list[tuple[Point, Point]] = []
        label_points: list[tuple[Point, str]] = []
        junctions: list[Point] = []
        no_connects: set[Point] = set()
        for wire in children(root, "wire"):
            pts = child(wire, "pts")
            if not isinstance(pts, list):
                continue
            points: list[Point] = []
            for xy in children(pts, "xy"):
                point = _key((_float(scalar(xy, 1)), _float(scalar(xy, 2))))
                points.append(point)
                ds.add(point)
            for a, b in zip(points, points[1:]):
                ds.union(a, b)
                segments.append((a, b))
        for kind in ("label", "global_label", "hierarchical_label"):
            for label in children(root, kind):
                name = scalar(label) or ""
                point, _ = _point_from_at(child(label, "at"))
                point = _key(point)
                ds.add(point)
                label_points.append((point, name))
        for junction in children(root, "junction"):
            point, _ = _point_from_at(child(junction, "at"))
            point = _key(point)
            ds.add(point)
            junctions.append(point)
        for marker in children(root, "no_connect"):
            point, _ = _point_from_at(child(marker, "at"))
            no_connects.add(_key(point))
        pin_points: list[tuple[Point, Component, Pin]] = []
        for component in components:
            for pin in component.pins:
                if pin.position is not None:
                    point = _key(pin.position)
                    ds.add(point)
                    pin_points.append((point, component, pin))
        anchors = [point for point, _ in label_points] + junctions + [point for point, _, _ in pin_points]
        for point in anchors:
            for a, b in segments:
                if _point_on_segment(point, a, b):
                    ds.union(point, a)
                    ds.union(point, b)
        labels_by_root: dict[Point, list[str]] = {}
        for point, name in label_points:
            if name:
                labels_by_root.setdefault(ds.find(point), []).append(name)
        for point, component, _ in pin_points:
            if component.lib_id.lower().startswith("power:"):
                labels_by_root.setdefault(ds.find(point), []).append(component.value or component.lib_id.split(":")[-1])
        pins_by_root: dict[Point, list[tuple[Component, Pin]]] = {}
        for point, component, pin in pin_points:
            pins_by_root.setdefault(ds.find(point), []).append((component, pin))
        roots = sorted(set(labels_by_root) | set(pins_by_root), key=lambda p: (p[0], p[1]))
        nets: list[Net] = []
        warnings: list[str] = []
        anonymous_index = 1
        for root_point in roots:
            labels = list(dict.fromkeys(labels_by_root.get(root_point, [])))
            connected = pins_by_root.get(root_point, [])
            if labels:
                name = labels[0]
                if len(labels) > 1:
                    warnings.append(f"multiple labels share one electrical net: {', '.join(labels)}")
            else:
                name = f"N${anonymous_index}"
                anonymous_index += 1
            pin_ids: list[str] = []
            for component, pin in connected:
                point = _key(pin.position or root_point)
                if point in no_connects and not labels and len(connected) == 1:
                    pin.net = None
                    continue
                pin.net = name
                pin_ids.append(f"{component.reference}.{pin.number}")
            if pin_ids or labels:
                nets.append(Net(name=name, labels=labels, pins=pin_ids))
        if not components:
            warnings.append("no schematic symbols were found")
        if components and not any(c.pins for c in components):
            warnings.append("symbols were found but pin geometry could not be resolved; check KiCad format compatibility")
        return nets, warnings
