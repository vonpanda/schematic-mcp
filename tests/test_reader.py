"""Reader tests cover source boundaries, portable output and actual KiCad rendering."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import shutil

import pytest

from schematic_mcp.models import Component, Net, Pin, Schematic
from schematic_mcp.reader import make_reader


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "minimal.kicad_sch"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 297 210"></svg>'


def fake_artwork(*_args):
    return [{"label": "minimal", "mime": "image/svg+xml",
             "image": base64.b64encode(SVG).decode("ascii"), "box": [0, 0, 297, 210]}]


@pytest.fixture
def fake_cli(monkeypatch):
    monkeypatch.setattr("schematic_mcp.reader._kicad_cli", lambda explicit: "fixture-cli")
    monkeypatch.setattr("schematic_mcp.reader._kicad_erc",
                        lambda source, cli: {"status": "complete", "findings": [], "ignored_checks": []})


def test_reader_is_portable_and_does_not_overwrite(tmp_path, monkeypatch, fake_cli):
    monkeypatch.setattr("schematic_mcp.reader._render_kicad", fake_artwork)
    output = tmp_path / "reader.html"
    result = make_reader(str(FIXTURE), output, root=str(FIXTURE.parent))
    html = output.read_text(encoding="utf-8")
    assert result["connectivity_status"] == "source_resolved"
    assert '"mime":"image/svg+xml"' in html
    assert 'p.mime+";base64,"+p.image' in html
    assert '"reference":"U1"' in html
    assert '"status":"needs_engineering_review"' in html
    assert "default-src 'none'" in html
    with pytest.raises(FileExistsError):
        make_reader(str(FIXTURE), output, root=str(FIXTURE.parent))
    assert output.read_text(encoding="utf-8") == html


def test_reader_rejects_root_escape_and_existing_output_before_render(tmp_path, monkeypatch, fake_cli):
    monkeypatch.setattr("schematic_mcp.reader._render_kicad", fake_artwork)
    with pytest.raises(PermissionError):
        make_reader(str(FIXTURE), tmp_path / "outside.html", root=str(tmp_path))
    link = tmp_path / "link.kicad_sch"
    link.symlink_to(FIXTURE)
    with pytest.raises(PermissionError):
        make_reader(str(link), tmp_path / "symlink.html", root=str(tmp_path))
    assert list(tmp_path.glob("*.html")) == []


def test_reader_escapes_untrusted_source_text(tmp_path, monkeypatch, fake_cli):
    from schematic_mcp.workspace import Workspace

    malicious = "</script><script>alert(1)</script>"
    model = Schematic(path=str(FIXTURE), format="kicad_sch",
                      components=[Component(reference="U1", value=malicious, lib_id="Test",
                                            pins=[Pin(number="1", net="N")])],
                      nets=[Net(name="N", pins=["U1.1"])],
                      provenance={"method": "native_parser",
                                  "sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest()})
    monkeypatch.setattr(Workspace, "open", lambda self, path: model)
    monkeypatch.setattr("schematic_mcp.reader._render_kicad", fake_artwork)
    output = tmp_path / "safe.html"
    make_reader(str(FIXTURE), output)
    html = output.read_text(encoding="utf-8")
    assert malicious not in html
    assert "\\u003c/script\\u003e" in html


def test_reader_vision_evidence_and_page_selection(tmp_path, monkeypatch):
    from PIL import Image
    from schematic_mcp.workspace import Workspace

    source = tmp_path / "drawing.png"
    Image.new("RGB", (80, 60), "white").save(source)
    model = Schematic(path=str(source), format="vision",
                      components=[Component(reference="P1/U1", value="IC", lib_id="",
                                            pins=[Pin(number="1", net="P1/n1",
                                                      evidence={"page": 1, "x0": .2, "y0": .3,
                                                                "x1": .4, "y1": .5})])],
                      nets=[Net(name="P1/n1", pins=["P1/U1.1"])],
                      provenance={"method": "llm_vision",
                                  "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    monkeypatch.setattr(Workspace, "extract", lambda self, path, pages: model)
    output = tmp_path / "vision.html"
    result = make_reader(str(source), output, vision=True, pages=[1])
    html = output.read_text(encoding="utf-8")
    assert result["connectivity_status"] == "unverified"
    assert '"page":1' in html
    assert '"mime":"image/png"' in html
    with pytest.raises(ValueError, match="--pages requires"):
        make_reader(str(FIXTURE), tmp_path / "invalid.html", pages=[1])
    assert not (tmp_path / "invalid.html").exists()


def test_actual_kicad_svg_export_round_trip(tmp_path):
    from schematic_mcp.workspace import Workspace

    cli = shutil.which("kicad-cli")
    if not cli and Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli").is_file():
        cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if not cli:
        pytest.skip("KiCad CLI unavailable")
    output = tmp_path / "native.html"
    result = make_reader(str(FIXTURE), output, kicad_cli=cli)
    assert result["pages"] == 1
    assert result["kicad_erc"]["status"] == "complete"
    assert result["kicad_erc"]["findings"] > 0
    project = Workspace().open_project(str(FIXTURE))
    assert project.provenance["hierarchy_complete"]
    assert next(c for c in project.components if c.reference == "U1").pins[0].net == "/SENSOR_OUT"
    html = output.read_text(encoding="utf-8")
    assert 'viewBox' in base64.b64decode(html.split('"image":"', 1)[1].split('"', 1)[0]).decode("utf-8")


def test_reader_rejects_source_changed_during_render(tmp_path, monkeypatch, fake_cli):
    source = tmp_path / "change.kicad_sch"
    source.write_bytes(FIXTURE.read_bytes())

    def changed(path, cli):
        source.write_bytes(source.read_bytes() + b"\n")
        return fake_artwork()

    monkeypatch.setattr("schematic_mcp.reader._render_kicad", changed)
    output = tmp_path / "changed.html"
    with pytest.raises(RuntimeError, match="Source changed"):
        make_reader(str(source), output, kicad_cli=__file__)
    assert not output.exists()
