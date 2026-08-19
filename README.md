# schematic-mcp

**Hardware schematic context for AI agents via MCP.**

`schematic-mcp` lets MCP-compatible agents inspect hardware schematics as structured electrical data instead of treating them as screenshots or long blobs of text.

> Status: **V0.1 / alpha**. The first adapter targets modern KiCad `.kicad_sch` files.

## Why this exists

An AI coding agent writing firmware often needs answers such as:

- Which ESP32 pin is connected to `SENSOR_OUT`?
- What is connected to `U4.GPIO12`?
- Which devices share this I2C net?
- What are all pins and resolved nets on the MCU?

The server parses the EDA file deterministically, builds a canonical component/pin/net model, and exposes that model through MCP tools and resources.

## V0.1 features

- Parse modern KiCad `.kicad_sch` S-expression files
- Read components, references, values and library IDs
- Resolve library pin geometry into schematic coordinates
- Select pins by the active KiCad unit for multi-unit symbols
- Build connectivity from wires, labels and junctions
- Resolve named and anonymous nets
- Inspect one component or pin
- Trace a pin to all endpoints on the same electrical net
- Generate compact MCU pin maps
- Expose the current canonical model as MCP resources
- Restrict filesystem access with `SCHEMATIC_MCP_ROOT` or `--root`
- Run locally over stdio or Streamable HTTP

## MCP tools

| Tool | Purpose |
| --- | --- |
| `open_schematic(path)` | Load a `.kicad_sch` file and build the circuit graph |
| `schematic_summary()` | Return counts, format info and parser warnings |
| `list_components(query="")` | Search components |
| `get_component(reference)` | Return component properties and pins |
| `get_pin(reference, pin_number)` | Return one pin and its net |
| `list_nets(query="")` | Search resolved nets |
| `get_net(name)` | Return labels and endpoints on a net |
| `trace_signal(reference, pin_number)` | Trace one pin across its electrical net |
| `get_mcu_pinmap(reference)` | Return a compact pin-to-net map |

Resources:
- `schematic://current/summary`
- `schematic://current/model`

## Install for development

Python 3.10+ is required.

```bash
git clone https://github.com/vonpanda/schematic-mcp.git
cd schematic-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The project uses the current stable v2 line of the official MCP Python SDK.

## Run

### Local stdio

```bash
schematic-mcp
```

or:

```bash
python -m schematic_mcp
```

You can restrict readable files without setting an environment variable:

```bash
schematic-mcp --root /absolute/path/to/your/hardware-projects
```

### Streamable HTTP

```bash
schematic-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

The MCP endpoint is available at `http://127.0.0.1:8000/mcp`. The default host is loopback-only; do not expose an unauthenticated development server directly to the public internet.

For the MCP Inspector:

```bash
mcp dev src/schematic_mcp/server.py
```

### Example MCP client configuration

```json
{
  "mcpServers": {
    "schematic": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/schematic-mcp", "run", "schematic-mcp"],
      "env": {"SCHEMATIC_MCP_ROOT": "/absolute/path/to/your/hardware-projects"}
    }
  }
}
```

Then an agent can call:

```text
open_schematic("board/main.kicad_sch")
get_component("U4")
get_mcu_pinmap("U4")
trace_signal("U4", "12")
```

## Filesystem security

By default, a local server can open paths accessible to its process. For agents you do not fully trust, set `SCHEMATIC_MCP_ROOT` or pass `--root` to an allowed project directory. Attempts to open files outside it are rejected.

## Current limitations

V0.1 is intentionally small. Hierarchical child sheets are discovered but not recursively merged into one cross-sheet graph yet. Unusual multi-unit/library constructs and third-party KiCad exports still need broader compatibility fixtures. Bus semantics are not reconstructed yet. PDF, Altium and EasyEDA are not implemented yet.

When connectivity cannot be resolved confidently, the project should surface a warning rather than invent an electrical connection. `trace_signal` follows only resolved net connectivity; it does not assume that separate pins inside an IC are electrically connected.

## Roadmap

- **V0.2** — hierarchical KiCad project graph and richer bus/net semantics
- **V0.3** — PDF/vector schematic adapter with confidence metadata
- **V0.4** — Altium and EasyEDA adapters
- **V0.5** — datasheet context and electrical-rule reasoning
- **V0.6** — firmware ↔ schematic pin-map validation
- **Later** — PCB, BOM, Gerber and manufacturing context

The long-term goal is a vendor-neutral **hardware context server for AI agents**.

## License and attribution

Licensed under the **Apache License 2.0**. Commercial use, modification and redistribution are allowed under the license terms. Redistributions must preserve the applicable copyright, license and NOTICE information as required by Apache-2.0.

See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Originally developed under **SYANKOR**.
