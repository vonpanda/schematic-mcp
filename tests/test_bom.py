import csv
import asyncio
import hashlib
import io
from pathlib import Path

import pytest

from schematic_mcp.bom import Bom, project_fingerprint, template
from schematic_mcp.knowledge import KnowledgeBase
from schematic_mcp.review import review_schematic
from schematic_mcp.workspace import Workspace
from schematic_mcp.reader import make_reader
from schematic_mcp.models import SheetRef
from mcp import Client
import schematic_mcp.server as server


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def write_bom(path, fingerprint, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Reference", "Manufacturer", "MPN", "Project SHA256"])
        for reference, maker, mpn in rows:
            writer.writerow([reference, maker, mpn, fingerprint])


def test_bom_fills_missing_mpn_and_report_carries_both_hashes(tmp_path):
    workspace = Workspace()
    model = workspace.open(str(EXAMPLES / "minimal.kicad_sch"))
    model.components[0].properties.pop("MPN", None)
    model.components[0].properties.pop("Manufacturer", None)
    path = tmp_path / "bom.csv"
    write_bom(path, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    bom = Bom.load(path, model)
    knowledge = KnowledgeBase.load(EXAMPLES / "knowledge/components.json")
    context = knowledge.context(model, bom)
    assert context["matched"][0]["identity_source"] == "bom"
    assert context["matched"][0]["facts"][0]["citation_id"] == "U1/vin-max"
    assert context["bom_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    report = review_schematic(model, knowledge=knowledge, bom=bom)
    assert report["bom"]["assigned"] == 1
    assert "U1" not in context["unresolved"].get("missing_mpn", [])


@pytest.mark.parametrize("rows,error", [
    ([("U9", "Example Semi", "X100")], "absent"),
    ([("U1", "Example Semi", "X100"), ("u1", "Example Semi", "X100")], "Duplicate"),
    ([("U1", "", "X100")], "blank"),
])
def test_bom_rejects_invalid_rows(tmp_path, rows, error):
    model = Workspace().open(str(EXAMPLES / "minimal.kicad_sch"))
    path = tmp_path / "bom.csv"
    write_bom(path, model.provenance["project_sha256"], rows)
    with pytest.raises(ValueError, match=error):
        Bom.load(path, model)


def test_bom_rejects_wrong_project_changed_file_and_symbol_conflict(tmp_path):
    model = Workspace().open(str(EXAMPLES / "minimal.kicad_sch"))
    path = tmp_path / "bom.csv"
    write_bom(path, "0" * 64, [("U1", "Example Semi", "X100")])
    with pytest.raises(ValueError, match="fingerprint"):
        Bom.load(path, model)
    write_bom(path, model.provenance["project_sha256"], [("U1", "Example Semi", "WRONG")])
    bom = Bom.load(path, model)
    knowledge = KnowledgeBase.load(EXAMPLES / "knowledge/components.json")
    assert knowledge.context(model, bom)["unresolved"]["conflicting_mpn_fields"] == ["U1"]
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="changed"):
        knowledge.context(model, bom)


def test_bom_rejects_imported_model_and_root_escape(tmp_path):
    workspace = Workspace()
    model = workspace.open(str(EXAMPLES / "minimal.kicad_sch"))
    outside = tmp_path / "outside.csv"
    write_bom(outside, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    link = allowed / "bom.csv"
    link.symlink_to(outside)
    with pytest.raises(PermissionError, match="outside"):
        Bom.load(link, model, allowed)
    model.provenance["method"] = "imported_json"
    with pytest.raises(ValueError, match="native KiCad"):
        Bom.load(outside, model)


def test_bom_rejects_root_only_parse_of_hierarchy(tmp_path):
    model = Workspace().open(str(EXAMPLES / "minimal.kicad_sch"))
    model.sheets.append(SheetRef(name="/child", file="child.kicad_sch"))
    path = tmp_path / "bom.csv"
    write_bom(path, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    with pytest.raises(ValueError, match="complete KiCad hierarchy"):
        Bom.load(path, model)


def test_bom_fingerprint_changes_with_child_sheet_and_template(tmp_path):
    root, child = tmp_path / "root.kicad_sch", tmp_path / "child.kicad_sch"
    root.write_text("root")
    child.write_text("child")
    first = project_fingerprint(root, {root: hashlib.sha256(root.read_bytes()).hexdigest(),
                                       child: hashlib.sha256(child.read_bytes()).hexdigest()})
    child.write_text("changed")
    second = project_fingerprint(root, {root: hashlib.sha256(root.read_bytes()).hexdigest(),
                                        child: hashlib.sha256(child.read_bytes()).hexdigest()})
    assert first != second
    model = Workspace().open(str(EXAMPLES / "minimal.kicad_sch"))
    rows = list(csv.DictReader(io.StringIO(template(model))))
    assert {row["Reference"] for row in rows} == {c.reference for c in model.components}
    assert all(row["Project SHA256"] == model.provenance["project_sha256"] for row in rows)


def test_reader_embeds_bom_evidence_and_rejects_old_revision(tmp_path, monkeypatch):
    from test_reader import fake_artwork
    monkeypatch.setattr("schematic_mcp.reader._kicad_cli", lambda explicit: "fixture-cli")
    monkeypatch.setattr("schematic_mcp.reader._render_kicad", fake_artwork)
    monkeypatch.setattr("schematic_mcp.reader._kicad_erc",
                        lambda source, cli: {"status": "complete", "findings": []})
    model = Workspace().open(str(EXAMPLES / "minimal.kicad_sch"))
    bom_path = tmp_path / "bom.csv"
    write_bom(bom_path, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    result = make_reader(str(EXAMPLES / "minimal.kicad_sch"), tmp_path / "reader.html",
                         knowledge=str(EXAMPLES / "knowledge/components.json"), bom=str(bom_path))
    assert result["pages"] >= 1
    html = (tmp_path / "reader.html").read_text()
    assert '"bom_sha256":"' in html
    assert '"identity_source":"bom_and_symbol"' in html
    write_bom(bom_path, "0" * 64, [("U1", "Example Semi", "X100")])
    with pytest.raises(ValueError, match="fingerprint"):
        make_reader(str(EXAMPLES / "minimal.kicad_sch"), tmp_path / "old.html",
                    knowledge=str(EXAMPLES / "knowledge/components.json"), bom=str(bom_path))
    assert not (tmp_path / "old.html").exists()


def test_workspace_bom_load_is_atomic_and_new_source_clears_binding(tmp_path):
    workspace = Workspace()
    model = workspace.open(str(EXAMPLES / "minimal.kicad_sch"))
    good, bad = tmp_path / "good.csv", tmp_path / "bad.csv"
    write_bom(good, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    write_bom(bad, "0" * 64, [("U1", "Example Semi", "X100")])
    loaded = workspace.load_bom(str(good))
    with pytest.raises(ValueError, match="fingerprint"):
        workspace.load_bom(str(bad))
    assert workspace.bom is loaded
    workspace.open(str(EXAMPLES / "esp32_firmware_validation.kicad_sch"))
    assert workspace.bom is None


def test_bom_rejects_source_mutation_after_binding(tmp_path):
    source = tmp_path / "drawing.kicad_sch"
    source.write_bytes((EXAMPLES / "minimal.kicad_sch").read_bytes())
    model = Workspace().open(str(source))
    path = tmp_path / "bom.csv"
    write_bom(path, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    bom = Bom.load(path, model)
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="source changed"):
        review_schematic(model, bom=bom)


def test_mcp_bom_to_component_knowledge_round_trip(tmp_path):
    source = tmp_path / "minimal.kicad_sch"
    source.write_bytes((EXAMPLES / "minimal.kicad_sch").read_bytes())
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    for name in ("components.json", "demo-device.pdf"):
        (knowledge_dir / name).write_bytes((EXAMPLES / "knowledge" / name).read_bytes())
    model = Workspace().open(str(source))
    bom_path = tmp_path / "bom.csv"
    write_bom(bom_path, model.provenance["project_sha256"], [("U1", "Example Semi", "X100")])
    previous = server.workspace
    current = Workspace()
    current.root = tmp_path
    server.workspace = current

    async def exercise():
        async with Client(server.mcp, raise_exceptions=True) as client:
            for name, args in (("open_schematic", {"path": "minimal.kicad_sch"}),
                               ("load_component_bom", {"path": "bom.csv"}),
                               ("load_component_knowledge", {"path": "knowledge/components.json"})):
                result = await client.call_tool(name, args)
                assert result.structured_content["ok"] is True
            matched = await client.call_tool("component_knowledge", {"reference": "U1"})
            assert matched.structured_content["status"] == "matched"
            assert matched.structured_content["part"]["identity_source"] == "bom_and_symbol"
            review = await client.call_tool("review_schematic", {})
            assert review.structured_content["review"]["bom"]["assigned"] == 1

    try:
        asyncio.run(exercise())
    finally:
        server.workspace = previous
