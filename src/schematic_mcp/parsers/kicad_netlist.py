"""Full-project KiCad XML netlist adapter; electrical facts come from KiCad CLI."""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from schematic_mcp.models import Component, Net, Pin, Schematic, SheetRef


def parse_kicad_netlist(xml: bytes, source: Path) -> Schematic:
    root = ET.fromstring(xml)
    if root.tag != "export":
        raise ValueError("Expected KiCad XML netlist")
    parts = {}
    for item in root.findall("./libparts/libpart"):
        key = (item.get("lib", ""), item.get("part", ""))
        parts[key] = {p.get("num"): p for p in item.findall("./pins/pin")}
    components = []
    by_ref = {}
    for item in root.findall("./components/comp"):
        reference = item.get("ref", "")
        if not reference or reference in by_ref:
            raise ValueError("KiCad XML contains a missing or duplicate reference")
        value = item.findtext("value", default="")
        libsource = item.find("libsource")
        lib = libsource.get("lib", "") if libsource is not None else ""
        part = libsource.get("part", "") if libsource is not None else ""
        properties = {p.get("name", ""): p.get("value", "") for p in item.findall("property")}
        sheetpath = item.find("sheetpath")
        sheet = sheetpath.get("names", "/") if sheetpath is not None else "/"
        properties["sheet_path"] = sheet
        pin_numbers = {p.get("num", "") for p in item.findall("./units/unit/pins/pin")}
        if not pin_numbers:
            pin_numbers = set(parts.get((lib, part), {}))
        pins = []
        for number in sorted(pin_numbers):
            if not number:
                continue
            definition = parts.get((lib, part), {}).get(number)
            pins.append(Pin(number=number, name=definition.get("name", "") if definition is not None else "",
                            electrical_type=definition.get("type", "") if definition is not None else "",
                            evidence={"path": str(source), "sheet": sheet, "reference": reference, "pin": number}))
        component = Component(reference=reference, value=value, lib_id=f"{lib}:{part}" if lib else part,
                              properties=properties, pins=pins,
                              evidence={"path": str(source), "sheet": sheet, "reference": reference})
        components.append(component)
        by_ref[reference] = component
    endpoints = {(c.reference, p.number): p for c in components for p in c.pins}
    nets = []
    names = set()
    assigned = set()
    for item in root.findall("./nets/net"):
        name = item.get("name", "")
        if not name or name in names:
            raise ValueError("KiCad XML contains a missing or duplicate net name")
        names.add(name)
        nodes = item.findall("node")
        if nodes and all("no_connect" in node.get("pintype", "") for node in nodes):
            for node in nodes:
                pin = endpoints.get((node.get("ref", ""), node.get("pin", "")))
                if pin is not None:
                    pin.no_connect = True
            continue
        ids = []
        for node in nodes:
            ref, number = node.get("ref", ""), node.get("pin", "")
            pin = endpoints.get((ref, number))
            if pin is None or (ref, number) in assigned:
                raise ValueError("KiCad XML net has an unknown or duplicate pin")
            assigned.add((ref, number))
            pin.net = name
            if "no_connect" in node.get("pintype", ""):
                pin.no_connect = True
            if not pin.name:
                pin.name = node.get("pinfunction", "")
            if not pin.electrical_type:
                pin.electrical_type = node.get("pintype", "")
            ids.append(f"{ref}.{number}")
        nets.append(Net(name=name, labels=[name] if not name.startswith("Net-(") else [], pins=ids,
                        evidence=[{"path": str(source), "method": "kicad_cli_netlist"}]))
    sheets = []
    for sheet in root.findall("./design/sheet"):
        name = sheet.get("name", "")
        if name == "/":
            continue
        sheets.append(SheetRef(name=name, file=sheet.findtext("./title_block/source", default=""),
                               uuid=sheet.get("uuid_path")))
    return Schematic(path=str(source), format="kicad_xml_netlist",
                     version=root.findtext("./design/tool", default=""),
                     components=components, nets=nets, sheets=sheets,
                     provenance={"method": "kicad_cli_netlist"})
