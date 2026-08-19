from __future__ import annotations

from pathlib import Path

from schematic_mcp.kicad import parse_kicad_text
from schematic_mcp.store import SchematicStore


SAMPLE = r'''
(kicad_sch
  (version 20231120)
  (generator schematic-mcp-test)
  (uuid 00000000-0000-0000-0000-000000000001)
  (lib_symbols
    (symbol "Test:MCU"
      (property "Reference" "U")
      (property "Value" "TEST_MCU")
      (symbol "MCU_1_1"
        (pin input line
          (at -5 0 0)
          (length 2.54)
          (name "IN")
          (number "1")
        )
        (pin output line
          (at 5 0 180)
          (length 2.54)
          (name "OUT")
          (number "2")
        )
      )
    )
  )
  (symbol
    (lib_id "Test:MCU")
    (at 10 10 0)
    (unit 1)
    (uuid 00000000-0000-0000-0000-000000000010)
    (property "Reference" "U1")
    (property "Value" "TEST_MCU")
    (pin "1" (uuid 00000000-0000-0000-0000-000000000011))
    (pin "2" (uuid 00000000-0000-0000-0000-000000000012))
  )
  (wire
    (pts (xy 0 10) (xy 5 10))
    (uuid 00000000-0000-0000-0000-000000000020)
  )
  (wire
    (pts (xy 15 10) (xy 20 10))
    (uuid 00000000-0000-0000-0000-000000000021)
  )
  (label "INPUT"
    (at 0 10 0)
    (uuid 00000000-0000-0000-0000-000000000030)
  )
  (global_label "OUTPUT"
    (shape output)
    (at 20 10 0)
    (uuid 00000000-0000-0000-0000-000000000031)
  )
)
'''


def test_parses_components_pins_and_named_nets() -> None:
    schematic = parse_kicad_text(SAMPLE, name="demo")

    assert schematic.version == "20231120"
    assert schematic.generator == "schematic-mcp-test"
    assert len(schematic.components) == 1

    u1 = schematic.component("U1")
    assert u1 is not None
    assert u1.value == "TEST_MCU"
    assert u1.lib_id == "Test:MCU"
    assert u1.pin("1") is not None
    assert u1.pin("1").name == "IN"
    assert u1.pin("1").net == "INPUT"
    assert u1.pin("2").name == "OUT"
    assert u1.pin("2").net == "OUTPUT"

    assert schematic.net("INPUT").pins == ["U1.1"]
    assert schematic.net("OUTPUT").pins == ["U1.2"]


def test_store_traces_pin_through_component_to_other_net(tmp_path: Path) -> None:
    path = tmp_path / "demo.kicad_sch"
    path.write_text(SAMPLE, encoding="utf-8")

    store = SchematicStore(root=tmp_path)
    item_id, _ = store.load(path)
    trace = store.trace_signal(item_id, "U1.1", max_depth=2)

    assert trace["start"] == "U1.1"
    assert {node["id"] for node in trace["nodes"]} == {"INPUT", "U1", "OUTPUT"}
    assert any(edge["pin"] == "1" and edge["net"] == "INPUT" for edge in trace["edges"])
    assert any(edge["pin"] == "2" and edge["net"] == "OUTPUT" for edge in trace["edges"])


def test_store_rejects_paths_outside_root(tmp_path: Path) -> None:
    store = SchematicStore(root=tmp_path / "allowed")
    outside = tmp_path / "outside.kicad_sch"
    outside.write_text(SAMPLE, encoding="utf-8")

    try:
        store.load(outside)
    except PermissionError:
        pass
    else:
        raise AssertionError("expected root restriction to reject outside path")
