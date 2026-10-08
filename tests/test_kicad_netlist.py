from pathlib import Path

import pytest

from schematic_mcp.parsers.kicad_netlist import parse_kicad_netlist
from schematic_mcp.reader import _project_sheets


XML = b"""<?xml version="1.0"?>
<export>
  <design><tool>Eeschema 10</tool>
    <sheet name="/" uuid_path="/"><title_block><source>root.kicad_sch</source></title_block></sheet>
    <sheet name="/POWER/" uuid_path="/one/"><title_block><source>power.kicad_sch</source></title_block></sheet>
  </design>
  <components>
    <comp ref="U1"><value>MCU</value><libsource lib="Demo" part="MCU"/>
      <property name="Sheetfile" value="root.kicad_sch"/><sheetpath names="/"/>
      <units><unit><pins><pin num="1"/><pin num="2"/></pins></unit></units></comp>
    <comp ref="U2"><value>REG</value><libsource lib="Demo" part="REG"/>
      <property name="Sheetfile" value="power.kicad_sch"/><sheetpath names="/POWER/"/>
      <units><unit><pins><pin num="3"/></pins></unit></units></comp>
  </components>
  <libparts>
    <libpart lib="Demo" part="MCU"><pins><pin num="1" name="VDD" type="power_in"/>
      <pin num="2" name="NC" type="unspecified"/></pins></libpart>
    <libpart lib="Demo" part="REG"><pins><pin num="3" name="OUT" type="power_out"/></pins></libpart>
  </libparts>
  <nets>
    <net code="1" name="+3V3"><node ref="U1" pin="1"/><node ref="U2" pin="3"/></net>
    <net code="2" name="unconnected-(U1-NC-Pad2)">
      <node ref="U1" pin="2" pintype="unspecified+no_connect"/></net>
  </nets>
</export>"""


def test_project_netlist_keeps_cross_sheet_net_and_explicit_nc():
    model = parse_kicad_netlist(XML, Path("/project/root.kicad_sch"))
    assert len(model.components) == 2
    assert model.nets[0].pins == ["U1.1", "U2.3"]
    assert len(model.nets) == 1
    assert model.components[0].pins[0].net == "+3V3"
    assert model.components[0].pins[1].no_connect
    assert model.components[0].pins[1].net is None
    assert model.components[1].properties["sheet_path"] == "/POWER/"
    assert model.connectivity_status == "source_resolved"


def test_project_netlist_rejects_invalid_references_and_duplicate_nodes():
    with pytest.raises(ValueError, match="duplicate reference"):
        parse_kicad_netlist(XML.replace(b'ref="U2"', b'ref="U1"'), Path("root.kicad_sch"))
    with pytest.raises(ValueError, match="duplicate pin"):
        parse_kicad_netlist(XML.replace(b'<node ref="U2" pin="3"/>',
                                         b'<node ref="U1" pin="1"/>'), Path("root.kicad_sch"))


def test_project_sheet_preflight_rejects_symlink_escape(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside.kicad_sch"
    outside.write_text("(kicad_sch (version 20250114))", encoding="utf-8")
    (root / "child.kicad_sch").symlink_to(outside)
    source = root / "root.kicad_sch"
    source.write_text('(kicad_sch (version 20250114) '
                      '(sheet (property "Sheetname" "child") '
                      '(property "Sheetfile" "child.kicad_sch")))', encoding="utf-8")
    with pytest.raises(PermissionError, match="outside"):
        _project_sheets(source, root.resolve())
