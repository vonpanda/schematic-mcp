"""MCP server exposing hardware schematic context to AI agents."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from schematic_mcp.workspace import Workspace
from schematic_mcp.review import review_schematic as run_review
from schematic_mcp.llm import JSONClient, LLMConfig

workspace = Workspace()
mcp = MCPServer(
    "SYANKOR Schematic MCP",
    version="0.1.0",
    instructions=(
        "Open a KiCad schematic, then use component/net/pin tools to inspect its "
        "electrical connectivity. Signal tracing is net-based and never invents "
        "internal connectivity through ICs. For PDF/images call extract_schematic explicitly; "
        "this sends drawings to an LLM API. Vision data is UNVERIFIED, never an exact netlist. "
        "Use review_schematic for local checks or review_schematic_with_llm for remote hypotheses."
    ),
)

_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

_OPEN_SCHEMATIC = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

_REMOTE_EXTRACTION = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True,
)
_REMOTE_REVIEW = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=False, open_world_hint=True,
)


@mcp.tool(annotations=_REMOTE_EXTRACTION)
def extract_schematic(path: str, pages: list[int] | None = None) -> dict[str, Any]:
    """Send PDF/image pages to the configured vision LLM and load an UNVERIFIED graph.

    This transmits drawing content and may incur API charges. Configure
    SCHEMATIC_LLM_API_KEY/MODEL/BASE_URL in the server environment.
    pages selects one-based PDF pages; omitted pages are not reviewed.
    """
    try:
        return {"ok": True, "summary": workspace.extract(path, pages).summary()}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def review_schematic() -> dict[str, Any]:
    """Run local electrical rules and return evidence-linked findings and coverage limits."""
    try:
        return {"ok": True, "review": run_review(workspace.require()[0])}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_REMOTE_REVIEW)
def review_schematic_with_llm() -> dict[str, Any]:
    """Send the current structured model to the configured LLM for review hypotheses.

    Transmits component, pin, net and source metadata; may incur API charges.
    Findings are not engineering sign-off and must cite existing endpoint IDs.
    """
    try:
        return {"ok": True, "review": run_review(workspace.require()[0], JSONClient(LLMConfig.from_env()))}
    except Exception as exc:
        return _error(exc)


def _error(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": type(exc).__name__, "message": str(exc)}


@mcp.tool(annotations=_OPEN_SCHEMATIC)
def open_schematic(path: str) -> dict[str, Any]:
    """Open a local KiCad .kicad_sch file and build its canonical circuit graph."""
    try:
        return {"ok": True, "summary": workspace.open(path).summary()}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_OPEN_SCHEMATIC)
def open_schematic_model(path: str) -> dict[str, Any]:
    """Load an exported/corrected canonical JSON graph offline; imported data stays UNVERIFIED."""
    try:
        return {"ok": True, "summary": workspace.open_model(path).summary()}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def schematic_summary() -> dict[str, Any]:
    """Return summary information for the currently loaded schematic."""
    try:
        schematic, _ = workspace.require()
        return {"ok": True, **schematic.summary()}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def list_components(query: str = "") -> dict[str, Any]:
    """List schematic components, optionally filtering by reference, value, or library id."""
    try:
        schematic, _ = workspace.require()
        needle = query.lower().strip()
        items = [
            {
                "reference": c.reference,
                "value": c.value,
                "lib_id": c.lib_id,
                "unit": c.unit,
                "pin_count": len(c.pins),
            }
            for c in schematic.components
            if not needle or needle in f"{c.reference} {c.value} {c.lib_id}".lower()
        ]
        return {"ok": True, "connectivity_status": schematic.connectivity_status, "count": len(items), "components": items}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def get_component(reference: str) -> dict[str, Any]:
    """Get one component including properties, pins, and resolved net names."""
    try:
        schematic, graph = workspace.require()
        component = graph.component(reference)
        if component is None:
            raise KeyError(f"component not found: {reference}")
        return {"ok": True, "connectivity_status": schematic.connectivity_status, "component": asdict(component)}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def get_pin(reference: str, pin_number: str) -> dict[str, Any]:
    """Get one component pin and its resolved electrical net."""
    try:
        schematic, graph = workspace.require()
        pin = graph.pin(reference, pin_number)
        if pin is None:
            raise KeyError(f"pin not found: {reference}.{pin_number}")
        return {"ok": True, "connectivity_status": schematic.connectivity_status, "reference": reference, "pin": asdict(pin)}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def list_nets(query: str = "") -> dict[str, Any]:
    """List resolved nets, optionally filtering by net name or connected pin."""
    try:
        schematic, _ = workspace.require()
        needle = query.lower().strip()
        items = [
            asdict(n)
            for n in schematic.nets
            if not needle or needle in f"{n.name} {' '.join(n.labels)} {' '.join(n.pins)}".lower()
        ]
        return {"ok": True, "connectivity_status": schematic.connectivity_status, "count": len(items), "nets": items}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def get_net(name: str) -> dict[str, Any]:
    """Get a net by exact name, including labels and all connected component pins."""
    try:
        schematic, graph = workspace.require()
        net = graph.net(name)
        if net is None:
            raise KeyError(f"net not found: {name}")
        return {"ok": True, "connectivity_status": schematic.connectivity_status, "net": asdict(net)}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def trace_signal(reference: str, pin_number: str) -> dict[str, Any]:
    """Trace one pin to every other pin on the same resolved electrical net."""
    try:
        schematic, graph = workspace.require()
        return {"ok": True, **graph.endpoints(reference, pin_number)}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def get_mcu_pinmap(reference: str) -> dict[str, Any]:
    """Return a compact pin-to-net map for an MCU or any multi-pin component."""
    try:
        schematic, graph = workspace.require()
        return {"ok": True, **graph.mcu_pinmap(reference)}
    except Exception as exc:
        return _error(exc)


@mcp.tool(annotations=_READ_ONLY)
def validate_pinmap(reference: str, expected: dict[str, str]) -> dict[str, Any]:
    """Compare firmware pin expectations with schematic nets.

    ``expected`` maps either physical pin numbers or unique symbolic pin names to
    expected net labels, for example ``{"GPIO8": "I2C_SDA"}``.
    """
    try:
        schematic, graph = workspace.require()
        return graph.validate_pinmap(reference, expected)
    except Exception as exc:
        return _error(exc)


@mcp.resource("schematic://current/summary")
def current_summary_resource() -> str:
    """Machine-readable summary of the current schematic."""
    try:
        schematic, _ = workspace.require()
        return json.dumps(schematic.summary(), ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps(_error(exc), ensure_ascii=False, indent=2)


@mcp.resource("schematic://current/model")
def current_model_resource() -> str:
    """Canonical JSON model for the currently loaded schematic."""
    try:
        schematic, _ = workspace.require()
        return json.dumps(schematic.to_dict(), ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps(_error(exc), ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expose hardware schematics through MCP")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port")
    parser.add_argument(
        "--root",
        help="Optional filesystem root that open_schematic is allowed to read",
    )
    args = parser.parse_args()

    if args.root:
        workspace.root = Path(args.root).expanduser().resolve()

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
