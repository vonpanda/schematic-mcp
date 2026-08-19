"""Read-only circuit graph helpers."""
from __future__ import annotations

from typing import Any

from schematic_mcp.models import Component, Net, Pin, Schematic


class CircuitGraph:
    def __init__(self, schematic: Schematic):
        self.schematic = schematic
        self._components = {c.reference.upper(): c for c in schematic.components}
        self._nets = {n.name: n for n in schematic.nets}

    def component(self, reference: str) -> Component | None:
        return self._components.get(reference.upper())

    def pin(self, reference: str, number: str) -> Pin | None:
        component = self.component(reference)
        if component is None:
            return None
        return next((p for p in component.pins if p.number == str(number)), None)

    def net(self, name: str) -> Net | None:
        return self._nets.get(name)

    def endpoints(self, reference: str, pin_number: str) -> dict[str, Any]:
        pin = self.pin(reference, pin_number)
        if pin is None:
            raise KeyError(f"pin not found: {reference}.{pin_number}")
        if not pin.net:
            return {"source": f"{reference}.{pin_number}", "net": None, "endpoints": [], "note": "pin is not connected to a resolved net"}
        net = self.net(pin.net)
        source = f"{reference}.{pin_number}".upper()
        return {"source": f"{reference}.{pin_number}", "net": pin.net, "labels": [] if net is None else net.labels, "endpoints": [] if net is None else [p for p in net.pins if p.upper() != source]}

    def mcu_pinmap(self, reference: str) -> dict[str, Any]:
        component = self.component(reference)
        if component is None:
            raise KeyError(f"component not found: {reference}")
        return {"reference": component.reference, "value": component.value, "lib_id": component.lib_id, "pins": [{"number": pin.number, "name": pin.name, "electrical_type": pin.electrical_type, "net": pin.net} for pin in component.pins]}
