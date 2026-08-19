from pathlib import Path

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.parsers.kicad import KiCadSchematicParser

EXAMPLE = Path(__file__).parents[1] / "examples" / "esp32_firmware_validation.kicad_sch"


def _graph() -> CircuitGraph:
    return CircuitGraph(KiCadSchematicParser().parse(EXAMPLE))


def test_validate_pinmap_detects_swapped_firmware_assignments():
    result = _graph().validate_pinmap(
        "U1",
        {
            "GPIO8": "I2C_SDA",
            "GPIO9": "I2C_SCL",
            "GPIO12": "LED_STATUS",
            "GPIO13": "SENSOR_INT",
        },
    )

    assert result["ok"] is False
    assert result["summary"] == {
        "total": 4,
        "matched": 2,
        "failed": 2,
        "mismatched": 2,
        "missing": 0,
        "unconnected": 0,
        "ambiguous": 0,
    }

    mismatches = {
        check["identifier"]: (check["expected_net"], check["actual_net"])
        for check in result["checks"]
        if check["status"] == "mismatch"
    }
    assert mismatches == {
        "GPIO12": ("LED_STATUS", "SENSOR_INT"),
        "GPIO13": ("SENSOR_INT", "LED_STATUS"),
    }


def test_validate_pinmap_accepts_physical_pin_number():
    result = _graph().validate_pinmap("U1", {"1": "I2C_SDA"})

    assert result["ok"] is True
    assert result["checks"][0]["pin_name"] == "GPIO8"
    assert result["checks"][0]["status"] == "match"


def test_validate_pinmap_reports_missing_identifier():
    result = _graph().validate_pinmap("U1", {"GPIO99": "SOMETHING"})

    assert result["ok"] is False
    assert result["summary"]["missing"] == 1
    assert result["checks"][0]["status"] == "missing"
