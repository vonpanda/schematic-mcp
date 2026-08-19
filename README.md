# schematic-mcp

MCP server that enables AI agents to understand, query, and reason over hardware schematics, components, nets, pins, and signal paths.

> **Status:** V0.1 alpha. The first adapter targets KiCad `.kicad_sch` schematics.

## Why this exists

AI coding agents can already read firmware, but hardware context is often trapped in EDA files or PDFs. `schematic-mcp` turns a schematic into a canonical electrical model and exposes that model through Model Context Protocol (MCP) tools and resources.

Instead of pasting a long hardware description into every prompt, an MCP-capable agent can ask questions such as:

- What is U4 and which nets are connected to it?
- Which net is U4 pin 12 on?
- Show the MCU pin-to-net map.
- What components are attached to `I2C_SDA`?
- Trace connectivity starting from `U4.12`.

## V0.1 capabilities

- Parse KiCad 6+ `.kicad_sch` S-expression files.
- Extract components, values, library IDs, properties, units and symbol pins.
- Reconstruct pin connection points from embedded KiCad symbol definitions.
- Parse wires, local labels, global labels, hierarchical labels and junctions.
- Rebuild electrical nets and assign named or generated nets to pins.
- Query components, pins and nets through MCP.
- Traverse the component ↔ net graph with `trace_signal`.
- Expose summary and full canonical-model MCP resources.
- Optionally restrict readable files to a configured filesystem root.

## Architecture

```text
Any MCP-capable Agent
        |
        v
+------------------------+
|     schematic-mcp      |
|  MCP tools/resources   |
+-----------+------------+
            |
            v
+------------------------+
| Canonical Schematic IR |
| Component / Pin / Net  |
+-----------+------------+
            |
            v
+------------------------+
|     KiCad Adapter      |
| .kicad_sch -> graph    |
+------------------------+
```

The canonical model is intentionally format-neutral so future adapters can target PDF, Altium, EasyEDA, PCB/BOM data and firmware cross-checking without changing the MCP query surface.

## Install

Python 3.10+ is required.

```bash
git clone https://github.com/vonpanda/schematic-mcp.git
cd schematic-mcp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
```

With `uv`:

```bash
uv sync --extra dev
```

## Run

### Local stdio MCP server

```bash
schematic-mcp
```

Optionally restrict the server to a hardware-project directory:

```bash
schematic-mcp --root /absolute/path/to/hardware-projects
```

The same restriction can be configured with:

```bash
export SCHEMATIC_MCP_ROOT=/absolute/path/to/hardware-projects
```

### Streamable HTTP

```bash
schematic-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

The MCP endpoint is then available on the SDK's standard Streamable HTTP path (`/mcp`).

## MCP client configuration

A typical stdio configuration looks like this (the exact settings UI depends on the MCP host):

```json
{
  "mcpServers": {
    "schematic": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/schematic-mcp",
        "run",
        "schematic-mcp",
        "--root",
        "/absolute/path/to/hardware-projects"
      ]
    }
  }
}
```

## Available tools

| Tool | Purpose |
|---|---|
| `open_schematic` | Load a local `.kicad_sch` file |
| `list_schematics` | Show loaded schematic IDs |
| `schematic_summary` | Return project metadata/counts |
| `list_components` | List references, values and pin counts |
| `find_components` | Search components and properties |
| `get_component` | Return a component and its resolved pins |
| `get_pin` | Return one pin and its resolved net |
| `get_pinmap` | Compact component pin-to-net mapping |
| `list_nets` | List reconstructed nets |
| `get_net` | Return one net, labels, points and pins |
| `trace_net` | Expand every component/pin on a net |
| `trace_signal` | Traverse the component ↔ net graph |

## Resources

```text
schematic://{schematic_id}/summary
schematic://{schematic_id}/model
```

## Example agent workflow

1. Call `open_schematic` with `/project/controller.kicad_sch`.
2. Call `find_components` with `ESP32`.
3. Call `get_pinmap` for the returned MCU reference.
4. Call `trace_signal` from a pin such as `U4.12` or a named net such as `I2C_SDA`.
5. Use that hardware context while generating or reviewing firmware.

## Current limitations

V0.1 is deliberately narrow. It does **not** yet claim complete KiCad netlist equivalence.

- Only `.kicad_sch` input is supported.
- Hierarchical child-sheet file traversal is not implemented yet.
- Complex symbol transformations and unusual third-party KiCad exports need broader fixture coverage.
- Bus semantics are not reconstructed yet.
- PDF/image schematic understanding is not part of V0.1.
- Altium/EasyEDA adapters are planned, not implemented.

When geometry cannot be resolved, the parser returns warnings rather than silently inventing a connection.

## Roadmap

- **V0.1:** KiCad components, pins, nets and signal tracing.
- **V0.2:** Hierarchical sheets, buses, stronger KiCad fixture coverage.
- **V0.3:** PDF/image schematic extraction with confidence metadata.
- **V0.4:** Datasheet-aware electrical checks.
- **V0.5:** Firmware ↔ schematic GPIO/interface validation.
- **Later:** PCB, BOM, Gerber and broader EDA adapters.

## Development

```bash
pytest -q
ruff check src tests
```

GitHub Actions runs the test suite on Python 3.10-3.13.

## License

Licensed under the **Apache License 2.0**. Commercial use, modification and redistribution are permitted subject to the license terms. Redistribution must preserve the notices required by Apache-2.0; see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Copyright 2026 SYANKOR.
