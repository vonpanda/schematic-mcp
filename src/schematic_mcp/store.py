"""In-memory project store and semantic query helpers."""

from __future__ import annotations

import os
from collections import deque
from pathlib import Path
from typing import Any

from .kicad import parse_kicad_file
from .models import Component, Net, Pin, Schematic


class SchematicNotFound(KeyError):
    pass


class SchematicStore:
    """Holds schematics loaded by MCP clients for the life of the server process."""

    def __init__(self, root: str | Path | None = None) -> None:
        configured = root if root is not None else os.getenv("SCHEMATIC_MCP_ROOT")
        self.root = Path(configured).expanduser().resolve() if configured else None
        self._items: dict[str, Schematic] = {}

    def _resolve(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser().resolve()
        if self.root is not None:
            try:
                candidate.relative_to(self.root)
            except ValueError as exc:
                raise PermissionError(
                    f"path is outside SCHEMATIC_MCP_ROOT ({self.root})"
                ) from exc
        return candidate

    def load(self, path: str | Path, schematic_id: str | None = None) -> tuple[str, Schematic]:
        resolved = self._resolve(path)
        schematic = parse_kicad_file(resolved)
        item_id = schematic_id or resolved.stem
        if not item_id.strip():
            raise ValueError("schematic_id cannot be empty")
        self._items[item_id] = schematic
        return item_id, schematic

    def get(self, schematic_id: str) -> Schematic:
        try:
            return self._items[schematic_id]
        except KeyError as exc:
            raise SchematicNotFound(
                f"schematic '{schematic_id}' is not loaded; call open_schematic first"
            ) from exc

    def ids(self) -> list[str]:
        return sorted(self._items)

    def component(self, schematic_id: str, reference: str) -> Component:
        schematic = self.get(schematic_id)
        component = schematic.component(reference)
        if component is None:
            raise KeyError(f"component '{reference}' not found")
        return component

    def pin(self, schematic_id: str, reference: str, number: str) -> Pin:
        component = self.component(schematic_id, reference)
        pin = component.pin(number)
        if pin is None:
            raise KeyError(f"pin '{reference}.{number}' not found")
        return pin

    def net(self, schematic_id: str, name: str) -> Net:
        schematic = self.get(schematic_id)
        net = schematic.net(name)
        if net is None:
            raise KeyError(f"net '{name}' not found")
        return net

    def trace_signal(self, schematic_id: str, start: str, max_depth: int = 3) -> dict[str, Any]:
        """Walk the bipartite component/net graph from a component, pin, or net."""
        schematic = self.get(schematic_id)
        if max_depth < 0 or max_depth > 12:
            raise ValueError("max_depth must be between 0 and 12")

        component_by_ref = {component.reference.upper(): component for component in schematic.components}
        net_by_name = {net.name: net for net in schematic.nets}

        pin_origin: str | None = None
        if "." in start:
            reference, number = start.rsplit(".", 1)
            pin = self.pin(schematic_id, reference, number)
            pin_origin = f"{reference.upper()}.{number}"
            if pin.net is None:
                return {"start": pin_origin, "nodes": [], "edges": [], "message": "pin has no net"}
            initial = ("net", pin.net)
        elif start.upper() in component_by_ref:
            initial = ("component", component_by_ref[start.upper()].reference)
        elif start in net_by_name:
            initial = ("net", start)
        else:
            raise KeyError(f"'{start}' is not a component reference, pin reference, or net name")

        queue: deque[tuple[str, str, int]] = deque([(initial[0], initial[1], 0)])
        visited: set[tuple[str, str]] = set()
        nodes: list[dict[str, Any]] = []
        edge_keys: set[tuple[str, str, str]] = set()
        edges: list[dict[str, str]] = []

        while queue:
            kind, identifier, depth = queue.popleft()
            key = (kind, identifier)
            if key in visited:
                continue
            visited.add(key)
            nodes.append({"type": kind, "id": identifier, "depth": depth})
            if depth >= max_depth:
                continue

            if kind == "component":
                component = component_by_ref[identifier.upper()]
                for pin in component.pins:
                    if pin.net is None:
                        continue
                    edge_key = (component.reference, pin.number, pin.net)
                    if edge_key not in edge_keys:
                        edge_keys.add(edge_key)
                        edges.append(
                            {
                                "component": component.reference,
                                "pin": pin.number,
                                "pin_name": pin.name,
                                "net": pin.net,
                            }
                        )
                    queue.append(("net", pin.net, depth + 1))
            else:
                net = net_by_name[identifier]
                for pin_ref in net.pins:
                    reference, number = pin_ref.rsplit(".", 1)
                    component = component_by_ref.get(reference.upper())
                    if component is None:
                        continue
                    pin = component.pin(number)
                    edge_key = (component.reference, number, net.name)
                    if edge_key not in edge_keys:
                        edge_keys.add(edge_key)
                        edges.append(
                            {
                                "component": component.reference,
                                "pin": number,
                                "pin_name": pin.name if pin else "",
                                "net": net.name,
                            }
                        )
                    queue.append(("component", component.reference, depth + 1))

        return {
            "start": pin_origin or start,
            "max_depth": max_depth,
            "nodes": nodes,
            "edges": edges,
        }
