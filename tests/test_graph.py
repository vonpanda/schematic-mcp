import pytest

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.models import Component, Net, Pin, Schematic


def _graph() -> CircuitGraph:
    schematic = Schematic(
        path="demo.kicad_sch",
        format="kicad_sch",
        components=[
            Component(
                reference="U1",
                value="MCU",
                lib_id="MCU:Demo",
                pins=[
                    Pin(number="1", name="NC"),
                    Pin(number="2", name="SDA", net="I2C_SDA"),
                ],
            ),
            Component(
                reference="U2",
                value="Sensor",
                lib_id="Sensor:Demo",
                pins=[Pin(number="1", name="SDA", net="I2C_SDA")],
            ),
        ],
        nets=[Net(name="I2C_SDA", labels=["I2C_SDA"], pins=["U1.2", "U2.1"])],
    )
    return CircuitGraph(schematic)


def test_component_lookup_is_case_insensitive():
    assert _graph().component("u1").reference == "U1"


def test_trace_excludes_source_endpoint():
    trace = _graph().endpoints("u1", "2")

    assert trace["net"] == "I2C_SDA"
    assert trace["endpoints"] == ["U2.1"]


def test_unconnected_pin_returns_explicit_note():
    trace = _graph().endpoints("U1", "1")

    assert trace["net"] is None
    assert trace["endpoints"] == []
    assert "not connected" in trace["note"]


def test_mcu_pinmap_keeps_pin_metadata():
    pinmap = _graph().mcu_pinmap("U1")

    assert pinmap["reference"] == "U1"
    assert pinmap["pins"][1] == {
        "number": "2",
        "name": "SDA",
        "electrical_type": "",
        "net": "I2C_SDA",
    }


def test_missing_pin_raises_key_error():
    with pytest.raises(KeyError, match="pin not found"):
        _graph().endpoints("U1", "99")
