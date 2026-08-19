"""KiCad .kicad_sch adapter.

The parser intentionally reads KiCad's text S-expression directly instead of
shelling out to KiCad.  It builds a format-neutral schematic model and derives
nets from wires, labels, junctions, and symbol pin connection points.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import Component, Net, Pin, Point, Schematic, Wire
from .sexpr import SExpr, atom, child, children, head, parse

_TOLERANCE = 1e-6
_UNIT_SUFFIX = re.compile(r"_(\d+)_(\d+)$")


class KiCadParseError(ValueError):
    """Raised when a file is not a supported KiCad schematic."""


@dataclass(frozen=True, slots=True)
class _LibPin:
    number: str
    name: str
    electrical_type: str
    position: Point
    unit: int


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[tuple[float, float], tuple[float, float]] = {}

    def add(self, item: tuple[float, float]) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: tuple[float, float]) -> tuple[float, float]:
        self.add(item)
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: tuple[float, float], right: tuple[float, float]) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def _float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: str, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _at(node: SExpr) -> tuple[Point, float]:
    value = child(node, "at")
    if not value or len(value) < 3:
        return Point(0.0, 0.0), 0.0
    x = _float(str(value[1]))
    y = _float(str(value[2]))
    rotation = _float(str(value[3])) if len(value) > 3 else 0.0
    return Point(x, y), rotation


def _uuid(node: SExpr) -> str | None:
    value = atom(node, "uuid")
    return value or None


def _properties(node: SExpr) -> dict[str, str]:
    result: dict[str, str] = {}
    for prop in children(node, "property"):
        if len(prop) >= 3 and isinstance(prop[1], str) and isinstance(prop[2], str):
            result[prop[1]] = prop[2]
    return result


def _find_first(node: SExpr, token: str) -> list[SExpr] | None:
    if not isinstance(node, list):
        return None
    if head(node) == token:
        return node
    for item in node[1:]:
        found = _find_first(item, token)
        if found is not None:
            return found
    return None


def _infer_unit(symbol_name: str) -> int:
    match = _UNIT_SUFFIX.search(symbol_name)
    return int(match.group(1)) if match else 0


def _parse_lib_pin(pin_node: list[SExpr], unit: int) -> _LibPin | None:
    if len(pin_node) < 3:
        return None
    electrical_type = str(pin_node[1])
    position, _ = _at(pin_node)
    name_node = child(pin_node, "name")
    number_node = child(pin_node, "number")
    if not number_node or len(number_node) < 2:
        return None
    name = str(name_node[1]) if name_node and len(name_node) > 1 else ""
    number = str(number_node[1])
    return _LibPin(number, name, electrical_type, position, unit)


def _walk_lib_pins(node: list[SExpr], inherited_unit: int = 0) -> Iterable[_LibPin]:
    current_unit = inherited_unit
    if head(node) == "symbol" and len(node) > 1 and isinstance(node[1], str):
        inferred = _infer_unit(node[1])
        if inferred or inherited_unit == 0:
            current_unit = inferred

    for pin_node in children(node, "pin"):
        parsed = _parse_lib_pin(pin_node, current_unit)
        if parsed is not None:
            yield parsed
    for symbol_node in children(node, "symbol"):
        yield from _walk_lib_pins(symbol_node, current_unit)


def _library(root: list[SExpr]) -> dict[str, list[_LibPin]]:
    lib_symbols = child(root, "lib_symbols")
    if not lib_symbols:
        return {}
    result: dict[str, list[_LibPin]] = {}
    for symbol_node in children(lib_symbols, "symbol"):
        if len(symbol_node) < 2 or not isinstance(symbol_node[1], str):
            continue
        result[symbol_node[1]] = list(_walk_lib_pins(symbol_node))
    return result


def _transform(local: Point, origin: Point, rotation: float, mirror: str = "") -> Point:
    x, y = local.x, local.y
    if mirror == "x":
        y = -y
    elif mirror == "y":
        x = -x

    radians = math.radians(rotation % 360.0)
    cos_a, sin_a = math.cos(radians), math.sin(radians)
    tx = x * cos_a - y * sin_a
    ty = x * sin_a + y * cos_a
    return Point(round(origin.x + tx, 6), round(origin.y + ty, 6))


def _lib_id(symbol_node: list[SExpr]) -> str:
    explicit = atom(symbol_node, "lib_id")
    if explicit:
        return explicit
    if len(symbol_node) > 1 and isinstance(symbol_node[1], str):
        return symbol_node[1]
    return ""


def _reference(symbol_node: list[SExpr], properties: dict[str, str]) -> str:
    if properties.get("Reference"):
        return properties["Reference"]
    reference = _find_first(symbol_node, "reference")
    if reference and len(reference) > 1:
        return str(reference[1])
    return "?"


def _component(symbol_node: list[SExpr], library: dict[str, list[_LibPin]]) -> Component:
    properties = _properties(symbol_node)
    lib_id = _lib_id(symbol_node)
    position, rotation = _at(symbol_node)
    unit = _int(atom(symbol_node, "unit", "1"), 1)
    mirror_node = child(symbol_node, "mirror")
    mirror = str(mirror_node[1]) if mirror_node and len(mirror_node) > 1 else ""

    instance_pin_nodes = children(symbol_node, "pin")
    instance_uuids: dict[str, str | None] = {}
    for pin_node in instance_pin_nodes:
        if len(pin_node) > 1:
            instance_uuids[str(pin_node[1])] = _uuid(pin_node)

    definitions = library.get(lib_id, [])
    selected: dict[str, _LibPin] = {}
    # Common unit (0) pins are loaded first; an exact unit definition wins.
    for definition in definitions:
        if definition.unit == 0:
            selected.setdefault(definition.number, definition)
    for definition in definitions:
        if definition.unit == unit:
            selected[definition.number] = definition

    pin_numbers = list(instance_uuids) or list(selected)
    pins: list[Pin] = []
    for number in pin_numbers:
        definition = selected.get(number)
        pins.append(
            Pin(
                number=number,
                name=definition.name if definition else "",
                electrical_type=definition.electrical_type if definition else "",
                position=(
                    _transform(definition.position, position, rotation, mirror)
                    if definition
                    else None
                ),
                uuid=instance_uuids.get(number),
            )
        )

    return Component(
        reference=_reference(symbol_node, properties),
        value=properties.get("Value", ""),
        lib_id=lib_id,
        unit=unit,
        position=position,
        rotation=rotation,
        properties=properties,
        pins=pins,
        uuid=_uuid(symbol_node),
    )


def _wire(wire_node: list[SExpr]) -> list[Wire]:
    pts = child(wire_node, "pts")
    if not pts:
        return []
    points: list[Point] = []
    for xy in children(pts, "xy"):
        if len(xy) >= 3:
            points.append(Point(_float(str(xy[1])), _float(str(xy[2]))))
    wire_uuid = _uuid(wire_node)
    return [Wire(left, right, wire_uuid) for left, right in zip(points, points[1:])]


def _label(node: list[SExpr], kind: str) -> tuple[str, str, Point] | None:
    if len(node) < 2 or not isinstance(node[1], str):
        return None
    position, _ = _at(node)
    return node[1], kind, position


def _point_on_segment(point: Point, wire: Wire) -> bool:
    ax, ay = wire.start.x, wire.start.y
    bx, by = wire.end.x, wire.end.y
    px, py = point.x, point.y
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > _TOLERANCE:
        return False
    return (
        min(ax, bx) - _TOLERANCE <= px <= max(ax, bx) + _TOLERANCE
        and min(ay, by) - _TOLERANCE <= py <= max(ay, by) + _TOLERANCE
    )


def _build_nets(
    components: list[Component],
    wires: list[Wire],
    labels: list[tuple[str, str, Point]],
    junctions: list[Point],
) -> list[Net]:
    uf = _UnionFind()
    point_lookup: dict[tuple[float, float], Point] = {}

    def add_point(point: Point) -> tuple[float, float]:
        key = point.key()
        uf.add(key)
        point_lookup.setdefault(key, point)
        return key

    for wire in wires:
        uf.union(add_point(wire.start), add_point(wire.end))
    for _, _, point in labels:
        add_point(point)
    for point in junctions:
        add_point(point)
    for component in components:
        for pin in component.pins:
            if pin.position is not None:
                add_point(pin.position)

    # Connect pins, labels, endpoints and explicit junctions that land anywhere
    # along a wire segment, not just at the segment's two stored endpoints.
    candidates = list(point_lookup.values())
    for wire in wires:
        start_key = wire.start.key()
        for point in candidates:
            if _point_on_segment(point, wire):
                uf.union(start_key, point.key())

    groups: dict[tuple[float, float], set[tuple[float, float]]] = {}
    for key in point_lookup:
        groups.setdefault(uf.find(key), set()).add(key)

    labels_by_root: dict[tuple[float, float], list[tuple[str, str]]] = {}
    for name, kind, point in labels:
        labels_by_root.setdefault(uf.find(point.key()), []).append((name, kind))

    pins_by_root: dict[tuple[float, float], list[tuple[Component, Pin]]] = {}
    for component in components:
        for pin in component.pins:
            if pin.position is not None:
                pins_by_root.setdefault(uf.find(pin.position.key()), []).append((component, pin))

    priority = {"global": 0, "hierarchical": 1, "local": 2}
    roots = sorted(groups, key=lambda root: (root[0], root[1]))
    root_names: dict[tuple[float, float], str] = {}
    anonymous = 1
    for root in roots:
        names = labels_by_root.get(root, [])
        if names:
            names = sorted(names, key=lambda item: (priority.get(item[1], 9), item[0]))
            root_names[root] = names[0][0]
        else:
            root_names[root] = f"N${anonymous}"
            anonymous += 1

    nets: list[Net] = []
    for root in roots:
        name = root_names[root]
        root_labels = sorted({item[0] for item in labels_by_root.get(root, [])})
        root_pins = pins_by_root.get(root, [])
        pin_refs = sorted(f"{component.reference}.{pin.number}" for component, pin in root_pins)
        for _, pin in root_pins:
            pin.net = name
        points = [point_lookup[key] for key in sorted(groups[root])]
        nets.append(Net(name=name, pins=pin_refs, labels=root_labels, points=points))
    return nets


def parse_kicad_text(text: str, *, source: str = "<memory>", name: str = "schematic") -> Schematic:
    """Parse a KiCad 6+ schematic document into the canonical model."""
    root_expr = parse(text)
    if not isinstance(root_expr, list) or head(root_expr) != "kicad_sch":
        raise KiCadParseError("document root is not kicad_sch")

    library = _library(root_expr)
    components = [_component(node, library) for node in children(root_expr, "symbol")]

    wires: list[Wire] = []
    for node in children(root_expr, "wire"):
        wires.extend(_wire(node))

    labels: list[tuple[str, str, Point]] = []
    for token, kind in (
        ("label", "local"),
        ("global_label", "global"),
        ("hierarchical_label", "hierarchical"),
    ):
        for node in children(root_expr, token):
            parsed_label = _label(node, kind)
            if parsed_label:
                labels.append(parsed_label)

    junctions = [_at(node)[0] for node in children(root_expr, "junction")]
    nets = _build_nets(components, wires, labels, junctions)

    warnings: list[str] = []
    unresolved = [
        f"{component.reference}.{pin.number}"
        for component in components
        for pin in component.pins
        if pin.position is None
    ]
    if unresolved:
        preview = ", ".join(unresolved[:10])
        suffix = " ..." if len(unresolved) > 10 else ""
        warnings.append(f"Could not resolve connection-point geometry for: {preview}{suffix}")

    return Schematic(
        name=name,
        source=source,
        format="kicad",
        version=atom(root_expr, "version"),
        generator=atom(root_expr, "generator"),
        components=components,
        nets=nets,
        wires=wires,
        warnings=warnings,
    )


def parse_kicad_file(path: str | Path) -> Schematic:
    """Read and parse a `.kicad_sch` file from disk."""
    schematic_path = Path(path).expanduser().resolve()
    if schematic_path.suffix.lower() != ".kicad_sch":
        raise KiCadParseError("V0.1 accepts .kicad_sch files only")
    text = schematic_path.read_text(encoding="utf-8")
    return parse_kicad_text(text, source=str(schematic_path), name=schematic_path.stem)
