import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from schematic_mcp.llm import JSONClient, LLMConfig, LLMError
from schematic_mcp.models import Component, Net, Pin, Schematic, SheetRef
from schematic_mcp.parsers.kicad import KiCadSchematicParser
from schematic_mcp.review import markdown_report, review_schematic
from test_vision import response


def circuit(types, lib_ids=None):
    components = [Component(f"U{i+1}", "Device", (lib_ids or [""] * len(types))[i],
                            pins=[Pin("1", electrical_type=kind, net="BUS")]) for i, kind in enumerate(types)]
    return Schematic(path="synthetic.kicad_sch", format="kicad_sch", components=components,
                     nets=[Net("BUS", pins=[f"U{i+1}.1" for i in range(len(types))])])


@pytest.mark.parametrize("types, expected", [
    (["output", "output", "input"], {"OUTPUT_CONFLICT"}),
    (["power_out", "power_out", "power_in"], {"POWER_OUTPUT_CONFLICT"}),
    (["input", "input"], {"INPUT_ONLY_NET"}),
    (["power_in"], {"ISOLATED_POWER_INPUT"}),
    (["open_collector", "open_collector", "input"], set()),
    (["tri_state", "tri_state", "input"], set()),
    (["output", "input"], set()),
    (["passive", "input"], set()),
])
def test_electrical_rules_positive_negative_and_shared_bus(types, expected):
    report = review_schematic(circuit(types))
    assert {f["rule"] for f in report["findings"]} == expected
    assert report["status"] == "needs_engineering_review"


def test_power_flags_not_counted_as_physical_power_drivers():
    report = review_schematic(circuit(["power_out", "power_out"], ["power:PWR_FLAG", "Regulator:Demo"]))
    assert not report["findings"]


def test_unknown_pin_and_unexpanded_hierarchy_never_get_clean_bill():
    model = circuit(["unspecified", "input"])
    model.sheets = [SheetRef("child", "child.kicad_sch")]
    model.warnings = ["unresolved geometry"]
    report = review_schematic(model)
    assert report["coverage"]["unknown_pin_types"] == 1
    assert report["source_warnings"] == ["unresolved geometry"]
    assert any("Child sheets" in s for s in report["limitations"])
    assert any("unknown" in s for s in report["limitations"])
    assert report["status"] != "pass"


def test_no_connect_marker_and_unresolved_input_are_distinct():
    model = circuit(["input", "input", "input"])
    model.components[0].pins[0].net = None
    model.components[0].pins[0].no_connect = True
    model.components[1].pins[0].net = None
    model.components[2].pins[0].no_connect = True
    model.nets[0].pins = ["U3.1"]
    report = review_schematic(model)
    rules = [(f["rule"], f["endpoints"]) for f in report["findings"]]
    assert ("UNRESOLVED_INPUT", ["U2.1"]) in rules
    assert ("NC_CONNECTED", ["U3.1"]) in rules
    assert all("U1.1" not in endpoints for _, endpoints in rules)


def test_native_no_connect_preserved_and_conflict_reported(tmp_path):
    example = Path(__file__).parents[1] / "examples" / "minimal.kicad_sch"
    text = example.read_text().replace('  (lib_symbols', '  (no_connect (at 10 10))\n  (lib_symbols')
    path = tmp_path / "nc.kicad_sch"
    path.write_text(text)
    model = KiCadSchematicParser().parse(path)
    assert model.components[0].pins[0].no_connect
    report = review_schematic(model)
    assert "NC_CONNECTED" in {f["rule"] for f in report["findings"]}


def test_duplicate_endpoint_skips_rules_instead_of_overwriting():
    model = circuit(["output", "output"])
    model.components[1].reference = "U1"
    report = review_schematic(model)
    assert not report["findings"]
    assert any("Ambiguous duplicate" in s for s in report["limitations"])


@pytest.mark.parametrize("endpoint", ["U1.1", "invented.99"])
def test_llm_review_citations_validated_and_evidence_attached(endpoint):
    content = {"findings": [{"severity": "warning", "title": "Check connection", "explanation": "Review supported net",
                            "endpoints": [endpoint], "recommendation": "Inspect source", "missing_information": ["datasheet"]}], "limitations": ["No datasheet"]}
    client = JSONClient(LLMConfig(model="test", api_key="test"), httpx.MockTransport(lambda _: httpx.Response(200, json=response(content))))
    if endpoint.startswith("invented"):
        with pytest.raises(LLMError, match="nonexistent"):
            review_schematic(circuit(["output", "input"]), client)
    else:
        report = review_schematic(circuit(["output", "input"]), client)
        assert report["findings"][0]["origin"] == "llm"
        assert report["findings"][0]["evidence"][0]["source"]["pin"] == "1"
        assert report["findings"][0]["missing_information"] == ["datasheet"]


def test_cli_native_exports_and_prevents_overwrite(tmp_path):
    output = tmp_path / "result"
    fixture = Path(__file__).parents[1] / "examples" / "minimal.kicad_sch"
    args = [sys.executable, "-m", "schematic_mcp.cli", str(fixture), "--output", str(output)]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True
    model = json.loads((output / "model.json").read_text())
    assert model["components"][0]["reference"] == "U1"
    original = (output / "model.json").read_bytes()
    assert "needs engineering review" in (output / "review.md").read_text()
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 1
    assert (output / "model.json").read_bytes() == original


def test_cli_keeps_local_artifacts_when_optional_remote_review_fails(tmp_path):
    import os
    output = tmp_path / "result"
    fixture = Path(__file__).parents[1] / "examples" / "minimal.kicad_sch"
    env = {k: v for k, v in os.environ.items() if not k.startswith("SCHEMATIC_LLM_")}
    result = subprocess.run([sys.executable, "-m", "schematic_mcp.cli", str(fixture), "--output", str(output), "--llm-review"], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert (output / "model.json").exists()
    assert json.loads((output / "review.json").read_text())["coverage"]["llm_review"] is False
    assert (output / "review.md").exists()
