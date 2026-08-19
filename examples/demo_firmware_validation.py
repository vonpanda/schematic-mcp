"""Run a deterministic firmware-vs-schematic pin validation demo."""
from __future__ import annotations

import json
import re
from pathlib import Path

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.parsers.kicad import KiCadSchematicParser

HERE = Path(__file__).resolve().parent
SCHEMATIC = HERE / "esp32_firmware_validation.kicad_sch"
FIRMWARE = HERE / "firmware_with_pin_bug.c"
GPIO_DEFINE = re.compile(r"^\s*#define\s+([A-Z][A-Z0-9_]*)_GPIO\s+(\d+)\b", re.MULTILINE)


def expected_pinmap_from_firmware(source: str) -> dict[str, str]:
    """Extract simple SIGNAL_GPIO numeric defines into GPIO-name -> net expectations."""
    return {f"GPIO{number}": signal for signal, number in GPIO_DEFINE.findall(source)}


def main() -> None:
    firmware = FIRMWARE.read_text(encoding="utf-8")
    expected = expected_pinmap_from_firmware(firmware)
    schematic = KiCadSchematicParser().parse(SCHEMATIC)
    result = CircuitGraph(schematic).validate_pinmap("U1", expected)

    print("Firmware expectations:")
    print(json.dumps(expected, indent=2))
    print("\nSchematic validation result:")
    print(json.dumps(result, indent=2))

    if result["ok"]:
        print("\nPASS: firmware pin assignments match the schematic.")
    else:
        print(f"\nMISMATCH DETECTED: {result['summary']['failed']} assignment(s) need review.")


if __name__ == "__main__":
    main()
