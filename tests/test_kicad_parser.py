from pathlib import Path

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.parsers.kicad import KiCadSchematicParser

EXAMPLE = Path(__file__).parents[1] / "examples" / "minimal.kicad_sch"


def test_parse_components_and_named_nets():
    schematic = KiCadSchematicParser().parse(EXAMPLE)
    assert schematic.format == "kicad_sch"
    assert {c.reference for c in schematic.components} == {"U1", "U2"}
    assert {n.name for n in schematic.nets} >= {"SENSOR_OUT", "GND"}


def test_pin_to_net_mapping():
    schematic = KiCadSchematicParser().parse(EXAMPLE)
    graph = CircuitGraph(schematic)
    assert graph.pin("U1", "1").net == "SENSOR_OUT"
    assert graph.pin("U2", "1").net == "SENSOR_OUT"
    assert graph.pin("U1", "2").net == "GND"


def test_signal_trace_returns_other_endpoint():
    schematic = KiCadSchematicParser().parse(EXAMPLE)
    trace = CircuitGraph(schematic).endpoints("U1", "1")
    assert trace["net"] == "SENSOR_OUT"
    assert "U2.1" in trace["endpoints"]
