"""MCP server exposing schematic semantics to AI agents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from mcp.server import MCPServer

from .store import SchematicStore

mcp = MCPServer("schematic-mcp")
store = SchematicStore()


@mcp.tool()
def open_schematic(path: str, schematic_id: str | None = None) -> dict[str, Any]:
    """Load a local KiCad .kicad_sch file and make it available to other tools."""
    item_id, schematic = store.load(path, schematic_id)
    return {"schematic_id": item_id, **schematic.summary()}


@mcp.tool()
def list_schematics() -> list[str]:
    """List schematic IDs loaded in this MCP server process."""
    return store.ids()


@mcp.tool()
def schematic_summary(schematic_id: str) -> dict[str, Any]:
    """Return high-level metadata and counts for a loaded schematic."""
    return store.get(schematic_id).summary()


@mcp.tool()
def list_components(schematic_id: str) -> list[dict[str, Any]]:
    """List components with reference, value, library ID, unit, and pin count."""
    return [
        {
            "reference": component.reference,
            "value": component.value,
            "lib_id": component.lib_id,
            "unit": component.unit,
            "pin_count": len(component.pins),
        }
        for component in store.get(schematic_id).components
    ]


@mcp.tool()
def find_components(schematic_id: str, query: str) -> list[dict[str, Any]]:
    """Find components by reference, value, library ID, or property text."""
    needle = query.casefold()
    results: list[dict[str, Any]] = []
    for component in store.get(schematic_id).components:
        haystack = " ".join(
            [
                component.reference,
                component.value,
                component.lib_id,
                *(f"{key} {value}" for key, value in component.properties.items()),
            ]
        ).casefold()
        if needle in haystack:
            results.append(component.to_dict())
    return results


@mcp.tool()
def get_component(schematic_id: str, reference: str) -> dict[str, Any]:
    """Return a component and all resolved pins/nets."""
    return store.component(schematic_id, reference).to_dict()


@mcp.tool()
def get_pin(schematic_id: str, reference: str, pin_number: str) -> dict[str, Any]:
    """Return one symbol pin, including its name, type, position, and resolved net."""
    return store.pin(schematic_id, reference, pin_number).to_dict()


@mcp.tool()
def get_pinmap(schematic_id: str, reference: str) -> list[dict[str, Any]]:
    """Return a compact pin-to-net map for a component such as an MCU or connector."""
    component = store.component(schematic_id, reference)
    return [
        {
            "number": pin.number,
            "name": pin.name,
            "electrical_type": pin.electrical_type,
            "net": pin.net,
        }
        for pin in component.pins
    ]


@mcp.tool()
def list_nets(schematic_id: str) -> list[dict[str, Any]]:
    """List all reconstructed electrical nets and the pins attached to each net."""
    return [
        {"name": net.name, "pins": net.pins, "labels": net.labels}
        for net in store.get(schematic_id).nets
    ]


@mcp.tool()
def get_net(schematic_id: str, net_name: str) -> dict[str, Any]:
    """Return a reconstructed net with labels, points, and connected pins."""
    return store.net(schematic_id, net_name).to_dict()


@mcp.tool()
def trace_net(schematic_id: str, net_name: str) -> dict[str, Any]:
    """Show every pin attached to a named net, with component and pin metadata."""
    net = store.net(schematic_id, net_name)
    attached: list[dict[str, Any]] = []
    for pin_ref in net.pins:
        reference, number = pin_ref.rsplit(".", 1)
        component = store.component(schematic_id, reference)
        pin = component.pin(number)
        attached.append(
            {
                "reference": component.reference,
                "value": component.value,
                "pin_number": number,
                "pin_name": pin.name if pin else "",
                "electrical_type": pin.electrical_type if pin else "",
            }
        )
    return {"net": net.name, "labels": net.labels, "attached": attached}


@mcp.tool()
def trace_signal(schematic_id: str, start: str, max_depth: int = 3) -> dict[str, Any]:
    """Traverse component↔net connectivity from a ref (U1), pin (U1.4), or net name."""
    return store.trace_signal(schematic_id, start, max_depth)


@mcp.resource("schematic://{schematic_id}/summary")
def summary_resource(schematic_id: str) -> str:
    """Machine-readable summary resource for a loaded schematic."""
    return json.dumps(store.get(schematic_id).summary(), ensure_ascii=False, indent=2)


@mcp.resource("schematic://{schematic_id}/model")
def model_resource(schematic_id: str) -> str:
    """Canonical full schematic model as JSON."""
    return json.dumps(store.get(schematic_id).to_dict(), ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expose hardware schematics over MCP")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--root",
        help="Optional filesystem root that open_schematic is allowed to read",
    )
    args = parser.parse_args()

    if args.root:
        store.root = Path(args.root).expanduser().resolve()

    transport: Literal["stdio", "streamable-http"] = args.transport
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            stateless_http=True,
            json_response=True,
        )


if __name__ == "__main__":
    main()
