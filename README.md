# schematic-mcp

[![CI](https://github.com/vonpanda/schematic-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/vonpanda/schematic-mcp/actions/workflows/ci.yml)

**Hardware schematic context for AI agents via MCP.**

`schematic-mcp` lets MCP-compatible agents inspect hardware schematics as structured electrical data instead of treating them as screenshots or long blobs of text.

> Status: **V0.1 / alpha**. The first adapter targets modern KiCad `.kicad_sch` files.

## Why this exists

An AI coding agent writing firmware often needs answers such as:

- Which ESP32 pin is connected to `SENSOR_OUT`?
- What is connected to `U4.GPIO12`?
- Which devices share this I2C net?
- What are all pins and resolved nets on the MCU?
- Does the GPIO map assumed by firmware actually match the schematic?

The server parses the EDA file deterministically, builds a canonical component/pin/net model, and exposes that model through MCP tools and resources.

The design principle is conservative: when connectivity cannot be resolved confidently, surface a warning instead of inventing an electrical connection.

### Design focus

`schematic-mcp` is intentionally a **file-driven hardware context layer**, not a general-purpose EDA GUI automation server. Normal KiCad read/query workflows do not require a running KiCad application. EDA-specific adapters produce a canonical electrical graph, while the agent-facing MCP contract remains format-neutral.

That makes the project complementary to editor/IPC automation: editor tools are valuable for interactive design changes, while `schematic-mcp` focuses on deterministic hardware facts that coding agents, CI systems, and future cross-EDA adapters can consume. Firmware ↔ schematic verification is a first concrete use case.

See [`docs/project-positioning.md`](docs/project-positioning.md) for the project boundaries and ecosystem thesis.

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
- Compare firmware pin expectations with schematic nets by physical pin number or symbolic pin name
- Expose the current canonical model as MCP resources
- Restrict filesystem access with `SCHEMATIC_MCP_ROOT` or `--root`
- Run locally over stdio or Streamable HTTP
- Automated parser, graph and filesystem-boundary tests in GitHub Actions

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
| `validate_pinmap(reference, expected)` | Compare firmware pin expectations with resolved schematic nets |

Resources:

- `schematic://current/summary`
- `schematic://current/model`

## Install from GitHub

Python 3.10+ is required. Until the first package-registry release is published, the current `main` branch can be installed directly from GitHub:

```bash
python -m pip install "git+https://github.com/vonpanda/schematic-mcp.git"
schematic-mcp --help
```

For reproducible production use, pin a release tag or commit rather than tracking an unpinned development branch. The first packaged release is tracked in [issue #8](https://github.com/vonpanda/schematic-mcp/issues/8).

## Install for development

```bash
git clone https://github.com/vonpanda/schematic-mcp.git
cd schematic-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The project uses the stable v2 line of the official MCP Python SDK.

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

### Try the included fixture

The repository contains a small synthetic KiCad schematic that is safe for demos and tests:

```bash
schematic-mcp --root "$PWD/examples"
```

Then an MCP-compatible client can call:

```text
open_schematic("minimal.kicad_sch")
schematic_summary()
list_components()
trace_signal("U1", "1")
```

The example should resolve `U1.1` onto `SENSOR_OUT` and show `U2.1` as another endpoint. See [`examples/README.md`](examples/README.md).

### Firmware ↔ schematic validation demo

A second synthetic example demonstrates a hardware bug that a coding agent cannot safely detect from source code alone. The firmware intentionally swaps `SENSOR_INT` and `LED_STATUS` GPIO assignments while the schematic preserves the correct electrical mapping.

Run the deterministic local demo:

```bash
python examples/demo_firmware_validation.py
```

It extracts the simple GPIO contract from `examples/firmware_with_pin_bug.c`, parses `examples/esp32_firmware_validation.kicad_sch`, and reports **two matches and two mismatches**.

Through MCP, the same comparison is:

```text
open_schematic("esp32_firmware_validation.kicad_sch")
validate_pinmap(
  "U1",
  {
    "GPIO8": "I2C_SDA",
    "GPIO9": "I2C_SCL",
    "GPIO12": "LED_STATUS",
    "GPIO13": "SENSOR_INT"
  }
)
```

See [`docs/firmware-validation-demo.md`](docs/firmware-validation-demo.md) for the full agent workflow and expected result.

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

By default, a local server can open paths accessible to its process. For agents you do not fully trust, set `SCHEMATIC_MCP_ROOT` or pass `--root` to an allowed project directory. Attempts to open files outside it are rejected, including paths that resolve outside the allowed root.

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting and deployment guidance.

## Current limitations

V0.1 is intentionally small. Hierarchical child sheets are discovered but not recursively merged into one cross-sheet graph yet. Unusual multi-unit/library constructs and third-party KiCad exports still need broader compatibility fixtures. Bus semantics are not reconstructed yet. PDF, Altium and EasyEDA are not implemented yet.

`trace_signal` follows only resolved net connectivity; it does not assume that separate pins inside an IC are electrically connected. `validate_pinmap` compares an explicit expected mapping; automatic extraction from arbitrary firmware frameworks is not part of the core parser yet.

## Roadmap

- **V0.2** — hierarchical KiCad project graph and richer bus/net semantics
- **V0.3** — PDF/vector schematic adapter with confidence metadata
- **V0.4** — Altium and EasyEDA adapters
- **V0.5** — datasheet context and electrical-rule reasoning
- **V0.6** — framework-specific firmware extraction (ESP-IDF/Arduino/Zephyr) and CI pin-contract checks
- **Later** — PCB, BOM, Gerber and manufacturing context

The long-term goal is a vendor-neutral **hardware context server for AI agents**.

## Contributing

Hardware engineers, embedded developers and EDA users can help most by contributing minimal compatibility fixtures, parser edge cases, tests, and real agent workflows.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). Coding agents and maintainers should also read [`AGENTS.md`](AGENTS.md) for architecture invariants, safety constraints, and the expected development loop. Please never contribute proprietary customer schematics unless you have explicit permission to publish them.

Useful maintainer/project docs:

- [`AGENTS.md`](AGENTS.md) — coding-agent and maintainer rules
- [`docs/project-positioning.md`](docs/project-positioning.md) — project boundaries and ecosystem value
- [`docs/architecture.md`](docs/architecture.md) — parser/model/MCP architecture
- [`docs/firmware-validation-demo.md`](docs/firmware-validation-demo.md) — firmware ↔ schematic mismatch demo
- [`examples/README.md`](examples/README.md) — runnable synthetic fixtures
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`SECURITY.md`](SECURITY.md) — security policy
- [`docs/oss-readiness.md`](docs/oss-readiness.md) — public-adoption and OSS-program readiness checklist

## License and attribution

Licensed under the **Apache License 2.0**. Commercial use, modification and redistribution are allowed under the license terms. Redistributions must preserve applicable copyright, license and NOTICE information as required by Apache-2.0.

See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Originally developed under **SYANKOR**.
