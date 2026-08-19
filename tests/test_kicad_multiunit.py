from pathlib import Path

from schematic_mcp.parsers.kicad import KiCadSchematicParser


MULTI_UNIT = r'''
(kicad_sch
  (version 20231120)
  (generator schematic-mcp-test)
  (lib_symbols
    (symbol "Test:Dual"
      (symbol "Dual_1_1"
        (pin input line
          (at -5 0 0)
          (name "A")
          (number "1")
        )
      )
      (symbol "Dual_2_1"
        (pin output line
          (at 5 0 180)
          (name "B")
          (number "2")
        )
      )
    )
  )
  (symbol
    (lib_id "Test:Dual")
    (at 10 10 0)
    (unit 2)
    (property "Reference" "U1")
    (property "Value" "DUAL")
    (pin "2")
  )
  (wire (pts (xy 15 10) (xy 20 10)))
  (label "UNIT2_OUT" (at 20 10 0))
)
'''


def test_only_active_kicad_symbol_unit_contributes_pins(tmp_path: Path):
    path = tmp_path / "multiunit.kicad_sch"
    path.write_text(MULTI_UNIT, encoding="utf-8")

    schematic = KiCadSchematicParser().parse(path)
    component = schematic.components[0]

    assert component.reference == "U1"
    assert component.unit == 2
    assert [pin.number for pin in component.pins] == ["2"]
    assert component.pins[0].name == "B"
    assert component.pins[0].net == "UNIT2_OUT"
