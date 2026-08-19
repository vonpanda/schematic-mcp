# Firmware ↔ schematic validation demo

This demo shows the core hardware-agent workflow that `schematic-mcp` is designed to unlock: an AI agent can compare assumptions in firmware with the actual electrical connectivity in a schematic instead of reasoning from source code alone.

All files in this demo are synthetic and safe to publish.

## Scenario

The schematic fixture `examples/esp32_firmware_validation.kicad_sch` contains a small ESP32-style MCU (`U1`) with these resolved nets:

| MCU pin name | Physical pin | Schematic net |
| --- | ---: | --- |
| `GPIO8` | 1 | `I2C_SDA` |
| `GPIO9` | 2 | `I2C_SCL` |
| `GPIO12` | 3 | `SENSOR_INT` |
| `GPIO13` | 4 | `LED_STATUS` |

The synthetic firmware fixture `examples/firmware_with_pin_bug.c` contains:

```c
#define I2C_SDA_GPIO 8
#define I2C_SCL_GPIO 9
#define SENSOR_INT_GPIO 13
#define LED_STATUS_GPIO 12
```

The I2C pins are correct, but the interrupt and status LED assignments are swapped.

## Run locally

Install the project in development mode, then run:

```bash
python examples/demo_firmware_validation.py
```

The demo extracts the simple `*_GPIO` macros, converts them to expected MCU pin-to-net relationships, parses the KiCad schematic, and compares the two views.

The expected result is **two matches and two mismatches**:

- `GPIO8`: firmware expects `I2C_SDA`, schematic resolves `I2C_SDA` → match
- `GPIO9`: firmware expects `I2C_SCL`, schematic resolves `I2C_SCL` → match
- `GPIO12`: firmware expects `LED_STATUS`, schematic resolves `SENSOR_INT` → mismatch
- `GPIO13`: firmware expects `SENSOR_INT`, schematic resolves `LED_STATUS` → mismatch

## Run through MCP

Start the MCP server with the examples directory as its filesystem boundary:

```bash
schematic-mcp --root "$PWD/examples"
```

An MCP-compatible agent can then use:

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

The tool returns a machine-readable result with per-pin statuses and a summary. A failed comparison returns `ok: false`; it does not silently reinterpret or rename nets.

## Why this matters for AI coding agents

A coding agent can read firmware and confidently produce code that compiles while still selecting the wrong hardware pin. The schematic is a separate source of truth. Exposing deterministic electrical connectivity through MCP lets the agent verify assumptions before it edits firmware or proposes a fix.

This initial capability deliberately does **not** attempt to parse every firmware framework. The MCP contract accepts an expected pin map so an agent, IDE integration, or future framework adapter can supply mappings extracted from ESP-IDF, Arduino, Zephyr, device-tree, board headers, configuration files, or other sources.

## Next steps

Future work can build on this primitive with:

- ESP-IDF/Arduino GPIO macro extraction;
- Zephyr devicetree and overlay adapters;
- automatic signal-name normalization with explicit confidence metadata;
- CI checks that fail when firmware pin contracts diverge from a schematic;
- suggestions for the smallest safe firmware or schematic change to resolve a mismatch.
