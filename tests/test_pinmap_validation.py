from pathlib import Path

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.parsers.kicad import KiCadSchematicParser

EXAMPLE = Path(__file__).parents[1] / "examples" / "esp32_firmware_validation.kicad_sch"


def _graph() -> CircuitGraph:
    return CircuitGraph(KiCadSchematicParser().parse(EXAMPLE))


def test_validate_pinmap_detects_firmware_mismatch_by_symbolic_pin_name():
    result = _graph().validate_pinmap(
        "U1",
        {
            "GPIO8": "I2C_SDA",
            "GPIO9": "I2C_SCL",
            "GPIO12": "SENSOR_INT",
            "GPIO13": "STATUS_LED",
        },
    )

    assert result["ok"] is False
    assert result["summary"] == {
        "total": 4,
        "matched": 3,
        "failed": 1,
        "mismatched": 1,
        "missing": 0,
        "unconnected": 0,
        "ambiguous": 0,
    }
    mismatch = next(check for check in result["checks"] if check["status"] == "mismatch")
    assert mismatch["identifier"] == "GPIO13"
    assert mismatch["expected_net"] == "STATUS_LED"
    assert mismatch["actual_net"] == "LED_STATUS"


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
