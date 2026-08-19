# Examples

This directory contains small, synthetic schematics that are safe to use in tests, demos, bug reports, and documentation.

Do not contribute proprietary customer schematics or files that contain confidential product information.

## Minimal KiCad example

`minimal.kicad_sch` is a deliberately small KiCad schematic used by the automated tests. It demonstrates:

- two components;
- a named `SENSOR_OUT` net;
- a `GND` net;
- pin-to-net resolution;
- signal tracing between endpoints.

## Try it through MCP

Start the server from the repository root:

```bash
schematic-mcp --root "$PWD/examples"
```

Then, from an MCP-compatible client, use this sequence:

```text
open_schematic("minimal.kicad_sch")
schematic_summary()
list_components()
get_component("U1")
trace_signal("U1", "1")
```

A successful trace for `U1.1` should resolve the `SENSOR_OUT` net and include `U2.1` as another endpoint.

## What makes a good fixture?

A fixture should be:

1. synthetic or explicitly licensed for public redistribution;
2. as small as possible while preserving the behavior being tested;
3. accompanied by a test that states the expected electrical interpretation;
4. named after the behavior or compatibility case it covers.

Future examples should cover hierarchical sheets, buses, multiple KiCad generations/exporters, and eventually other EDA formats.
