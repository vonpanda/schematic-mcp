import json
from pathlib import Path

import pytest

from schematic_mcp.model_io import load_model
from schematic_mcp.workspace import Workspace
from test_review import circuit


def test_export_reload_edit_and_review_stays_unverified(tmp_path):
    model = circuit(["output", "input"])
    model.provenance = {"method": "native_parser"}
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model.to_dict()))
    workspace = Workspace()
    result = workspace.open_model(str(path))
    assert result.connectivity_status == "unverified"
    assert result.provenance["original_method"] == "native_parser"
    assert workspace.graph.endpoints("U1", "1")["endpoints"] == ["U2.1"]
    assert not workspace.graph.validate_pinmap("U1", {"1": "BUS"})["ok"]
    assert json.loads(json.dumps(result.to_dict()))["nets"][0]["pins"] == ["U1.1", "U2.1"]


@pytest.mark.parametrize("mutation", [
    lambda d: d["nets"][0]["pins"].append("U1.1"),
    lambda d: d["nets"][0]["pins"].append("U99.1"),
    lambda d: d["nets"][0].update(pins=[]),
    lambda d: d["components"][0]["pins"][0].update(net="OTHER"),
    lambda d: d["components"].append(d["components"][0]),
    lambda d: d["components"][0]["pins"].append(d["components"][0]["pins"][0]),
    lambda d: d["nets"].append(d["nets"][0]),
])
def test_corrupt_canonical_graph_rejected(tmp_path, mutation):
    model = circuit(["output", "input"]).to_dict()
    mutation(model)
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError):
        load_model(path)


def test_failed_json_import_preserves_previous_workspace(tmp_path):
    workspace = Workspace()
    original = workspace.open(str(Path(__file__).parents[1] / "examples" / "minimal.kicad_sch"))
    path = tmp_path / "invalid.json"
    path.write_text('{"path":"secret"}')
    with pytest.raises(ValueError):
        workspace.open_model(str(path))
    assert workspace.require()[0] is original
