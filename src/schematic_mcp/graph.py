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

    def pin_by_identifier(self, reference: str, identifier: str) -> Pin | None:
        """Resolve a pin by physical pin number first, then by unique symbolic pin name."""
        component = self.component(reference)
        if component is None:
            return None

        key = str(identifier)
        numbered = [pin for pin in component.pins if pin.number == key]
        if numbered:
            return numbered[0]

        named = [pin for pin in component.pins if pin.name.casefold() == key.casefold()]
        if len(named) == 1:
            return named[0]
        if len(named) > 1:
            matches = ", ".join(pin.number for pin in named)
            raise ValueError(
                f"ambiguous pin identifier {reference}.{identifier}: "
                f"symbolic name matches physical pins {matches}"
            )
        return None

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

    def validate_pinmap(self, reference: str, expected: dict[str, str]) -> dict[str, Any]:
        """Compare firmware pin expectations with the schematic's resolved electrical nets.

        Keys in ``expected`` may be physical pin numbers (for example ``"17"``)
        or unique symbolic pin names (for example ``"GPIO8"``). Values are the
        expected schematic net labels.
        """
        component = self.component(reference)
        if component is None:
            raise KeyError(f"component not found: {reference}")

        checks: list[dict[str, Any]] = []
        counts = {"match": 0, "mismatch": 0, "missing": 0, "unconnected": 0, "ambiguous": 0}

        for identifier, expected_net in expected.items():
            identifier = str(identifier)
            expected_net = str(expected_net)
            try:
                pin = self.pin_by_identifier(reference, identifier)
            except ValueError as exc:
                counts["ambiguous"] += 1
                checks.append(
                    {
                        "identifier": identifier,
                        "expected_net": expected_net,
                        "status": "ambiguous",
                        "message": str(exc),
                    }
                )
                continue

            if pin is None:
                counts["missing"] += 1
                checks.append(
                    {
                        "identifier": identifier,
                        "expected_net": expected_net,
                        "status": "missing",
                        "message": f"pin identifier not found on {component.reference}",
                    }
                )
                continue

            if pin.net is None:
                counts["unconnected"] += 1
                checks.append(
                    {
                        "identifier": identifier,
                        "pin_number": pin.number,
                        "pin_name": pin.name,
                        "expected_net": expected_net,
                        "actual_net": None,
                        "status": "unconnected",
                    }
                )
                continue

            status = "match" if pin.net == expected_net else "mismatch"
            counts[status] += 1
            checks.append(
                {
                    "identifier": identifier,
                    "pin_number": pin.number,
                    "pin_name": pin.name,
                    "expected_net": expected_net,
                    "actual_net": pin.net,
                    "status": status,
                }
            )

        failed = counts["mismatch"] + counts["missing"] + counts["unconnected"] + counts["ambiguous"]
        return {
            "ok": failed == 0,
            "reference": component.reference,
            "value": component.value,
            "summary": {
                "total": len(checks),
                "matched": counts["match"],
                "failed": failed,
                "mismatched": counts["mismatch"],
                "missing": counts["missing"],
                "unconnected": counts["unconnected"],
                "ambiguous": counts["ambiguous"],
            },
            "checks": checks,
        }
