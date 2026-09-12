"""Adversarial contracts, actual image/PDF rendering and round-trip workflow tests."""
import asyncio
import copy
import io
import json
from pathlib import Path

import httpx
import pytest
from mcp import Client
from PIL import Image
from pydantic import ValidationError

from schematic_mcp.graph import CircuitGraph
from schematic_mcp.llm import JSONClient, LLMConfig, LLMError
from schematic_mcp.parsers.vision import canonicalize, image_content, render_pages
from schematic_mcp.parsers.vision_schema import PageExtraction
from schematic_mcp.review import markdown_report, review_schematic
from schematic_mcp.workspace import Workspace

EVIDENCE = dict(x0=0.1, y0=0.1, x1=0.8, y1=0.8, observation="Visible pin and continuous wire", confidence=0.95)
EXAMPLES = Path(__file__).parents[1] / "examples"


def extraction():
    return dict(schema_version="1.0", coverage="complete", warnings=[],
                components=[dict(reference=ref, value="Test driver", lib_id="", evidence=EVIDENCE,
                                 pins=[dict(number="1", name="OUT", electrical_type="output",
                                            net_id="n1", no_connect=False, evidence=EVIDENCE)]) for ref in ("U1", "U2")],
                nets=[dict(id="n1", name="BUS", scope="local", labels=["BUS"], evidence=EVIDENCE)])


def response(data=None, finish="stop", refusal=None):
    return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(data if data is not None else extraction()), "refusal": refusal}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}


def client(handler=None, **config):
    return JSONClient(LLMConfig(model="test-vision", api_key="test-secret", retries=0, **config),
                      httpx.MockTransport(handler or (lambda _: httpx.Response(200, json=response()))))


def make_image(path, size=(300, 200)):
    Image.new("RGB", size, "white").save(path)
    return path


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(unexpected="data"),
    lambda d: d.update(schema_version="2"),
    lambda d: d["components"].append(copy.deepcopy(d["components"][0])),
    lambda d: d["components"][0]["pins"].append(copy.deepcopy(d["components"][0]["pins"][0])),
    lambda d: d["components"][0]["pins"][0].update(net_id="missing"),
    lambda d: d["components"][0]["pins"][0].update(number=1),
    lambda d: d["components"][0].update(reference="U1.1"),
    lambda d: d["components"][0]["evidence"].update(confidence=1.1),
    lambda d: d["components"][0]["evidence"].update(confidence=float("nan")),
    lambda d: d["components"][0]["evidence"].update(x1=0.05),
    lambda d: d["nets"].append(copy.deepcopy(d["nets"][0])),
    lambda d: d["nets"].append({**copy.deepcopy(d["nets"][0]), "id": "unused"}),
])
def test_schema_rejects_ambiguous_or_invalid_data(mutation):
    data = copy.deepcopy(extraction())
    mutation(data)
    with pytest.raises(ValidationError):
        PageExtraction.model_validate(data)


def test_vision_graph_trace_review_and_pinmap_preserve_uncertainty(tmp_path):
    path = make_image(tmp_path / "circuit.png")
    workspace = Workspace()
    model = workspace.extract(str(path), client=client())
    assert model.provenance["usage"][0]["total_tokens"] == 150
    assert len(model.provenance["sha256"]) == 64
    graph = workspace.graph
    trace = graph.endpoints("P1/U1", "1")
    assert trace["endpoints"] == ["P1/U2.1"]
    assert trace["connectivity_status"] == "unverified"
    assert graph.mcu_pinmap("P1/U1")["connectivity_status"] == "unverified"
    validation = graph.validate_pinmap("P1/U1", {"1": "P1/n1:BUS"})
    assert not validation["ok"]
    assert validation["checks"][0]["status"] == "unverified"
    assert not graph.validate_pinmap("P1/U1", {})["ok"]
    report = review_schematic(model)
    assert report["findings"][0]["rule"] == "OUTPUT_CONFLICT"
    assert report["findings"][0]["evidence"][0]["source"]["page"] == 1
    assert report["findings"][0]["connectivity_status"] == "unverified"
    assert "page 1, box" in markdown_report(report)
    assert json.loads(json.dumps(model.to_dict()))["components"][0]["pins"][0]["evidence"]["page"] == 1


def test_local_labels_not_merged_but_explicit_globals_are(tmp_path):
    data = extraction()
    page = PageExtraction.model_validate(data)
    model = canonicalize(tmp_path / "test.pdf", [(1, page), (2, page)], {"model": "test"})
    assert len(model.nets) == 2
    assert len(model.nets[0].pins) == 2
    data["nets"][0]["scope"] = "global"
    page = PageExtraction.model_validate(data)
    model = canonicalize(tmp_path / "test.pdf", [(1, page), (2, page)], {"model": "test"})
    assert len(model.nets) == 1
    assert len(model.nets[0].pins) == 4
    assert len(model.nets[0].evidence) == 2
    assert model.connectivity_status == "unverified"


def test_same_display_label_different_net_ids_stay_separate(tmp_path):
    data = extraction()
    data["nets"].append({**data["nets"][0], "id": "n2"})
    data["components"][1]["pins"][0]["net_id"] = "n2"
    model = canonicalize(tmp_path / "test.png", [(1, PageExtraction.model_validate(data))], {"model": "test"})
    assert len({net.name for net in model.nets}) == 2


@pytest.mark.parametrize("pages", [[], [0], [-1], [2], [1, 1], [True]])
def test_image_page_selection_rejected_before_network(tmp_path, pages):
    path = make_image(tmp_path / "x.png")
    with pytest.raises(ValueError):
        list(render_pages(path, pages))


def test_real_multipage_pdf_rendering_and_page_order(tmp_path):
    # Synthetic test document generated in-memory; no customer artifacts.
    a, b = Image.new("RGB", (300, 200), "white"), Image.new("RGB", (300, 200), "black")
    path = tmp_path / "two.pdf"
    a.save(path, save_all=True, append_images=[b])
    pages = list(render_pages(path, [2, 1]))
    assert [number for number, _ in pages] == [1, 2]
    with Image.open(io.BytesIO(pages[0][1])) as first:
        assert first.getpixel((10, 10))[0] > 240
    with Image.open(io.BytesIO(pages[1][1])) as second:
        assert second.getpixel((10, 10))[0] < 10
    with pytest.raises(ValueError):
        list(render_pages(path, [1, 3]))


def test_detail_tiles_include_overview_and_are_bounded(tmp_path):
    path = make_image(tmp_path / "large.png", (6000, 3000))
    parts = image_content(1, path.read_bytes())
    images = [p for p in parts if p["type"] == "image_url"]
    assert 2 < len(images) <= 17
    assert "Whole-page overview" in parts[0]["text"]
    assert all(p["image_url"]["url"].startswith("data:image/png;base64,") for p in images)


@pytest.mark.parametrize("kind", ["parent", "absolute", "symlink"])
def test_vision_read_boundaries_before_client_call(tmp_path, kind):
    root = tmp_path / "root"
    root.mkdir()
    outside = make_image(tmp_path / "outside.png")
    workspace = Workspace()
    workspace.root = root.resolve()
    (root / "link.png").symlink_to(outside)
    path = {"parent": "../outside.png", "absolute": str(outside), "symlink": "link.png"}[kind]
    def forbidden(_):
        pytest.fail("Should not contact provider for a forbidden path")
    with pytest.raises(PermissionError):
        workspace.extract(path, client=client(forbidden))


def test_failure_preserves_loaded_state_then_native_reopen_resets_trust(tmp_path):
    workspace = Workspace()
    original = workspace.open(str(EXAMPLES / "minimal.kicad_sch"))
    path = make_image(tmp_path / "test.png")
    with pytest.raises(LLMError):
        workspace.extract(str(path), client=client(lambda _: httpx.Response(200, json=response({"bad": "data"}))))
    assert workspace.schematic is original
    workspace.extract(str(path), client=client())
    assert workspace.schematic.connectivity_status == "unverified"
    native = workspace.open(str(EXAMPLES / "minimal.kicad_sch"))
    assert native.connectivity_status == "source_resolved"
    assert workspace.graph.endpoints("U1", "1")["net"] == "SENSOR_OUT"


def test_later_page_failure_does_not_commit_partial_graph(tmp_path):
    image = Image.new("RGB", (100, 100), "white")
    path = tmp_path / "two.pdf"
    image.save(path, save_all=True, append_images=[image])
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=response() if len(calls) == 1 else response({}, finish="length"))
    workspace = Workspace()
    original = workspace.open(str(EXAMPLES / "minimal.kicad_sch"))
    with pytest.raises(LLMError, match="incomplete"):
        workspace.extract(str(path), client=client(handler))
    assert len(calls) == 2
    assert workspace.schematic is original


def test_mcp_vision_review_and_native_round_trip(tmp_path, monkeypatch):
    import schematic_mcp.server as server
    make_image(tmp_path / "drawing.png")
    workspace = Workspace()
    workspace.root = tmp_path.resolve()
    monkeypatch.setattr(server, "workspace", workspace)
    monkeypatch.setattr(LLMConfig, "from_env", classmethod(lambda cls: LLMConfig(model="test", api_key="test-secret")))
    original_request = JSONClient.request
    def mocked_request(self, schema, system, content):
        self.transport = httpx.MockTransport(lambda _: httpx.Response(200, json=response()))
        return original_request(self, schema, system, content)
    monkeypatch.setattr(JSONClient, "request", mocked_request)
    async def exercise():
        async with Client(server.mcp, raise_exceptions=True) as mcp_client:
            result = await mcp_client.call_tool("extract_schematic", {"path": "drawing.png"})
            assert result.structured_content["summary"]["connectivity_status"] == "unverified"
            result = await mcp_client.call_tool("review_schematic", {})
            assert result.structured_content["review"]["findings"][0]["rule"] == "OUTPUT_CONFLICT"
            for name, args in [("get_pin", {"reference": "P1/U1", "pin_number": "1"}),
                               ("get_component", {"reference": "P1/U1"}), ("list_components", {}),
                               ("list_nets", {}), ("get_net", {"name": "P1/n1:BUS"})]:
                result = await mcp_client.call_tool(name, args)
                assert result.structured_content["connectivity_status"] == "unverified"
            result = await mcp_client.call_tool("extract_schematic", {"path": "../outside.png"})
            assert result.structured_content["ok"] is False
            assert workspace.schematic.connectivity_status == "unverified"
    asyncio.run(exercise())


def test_visible_nc_and_wire_conflict_is_retained_for_review(tmp_path):
    data = extraction()
    data["components"][0]["pins"][0]["no_connect"] = True
    model = canonicalize(tmp_path / "nc.png", [(1, PageExtraction.model_validate(data))], {"model": "test"})
    report = review_schematic(model)
    assert "NC_CONNECTED" in {f["rule"] for f in report["findings"]}


def test_selected_pages_remain_explicitly_incomplete(tmp_path):
    model = canonicalize(tmp_path / "test.pdf", [(2, PageExtraction.model_validate(extraction()))], {"model": "test", "selected_pages": [2]})
    assert any("other document pages" in w for w in model.warnings)
    assert model.components[0].reference == "P2/U1"


def test_vision_hash_and_images_use_same_snapshot_if_file_changes(tmp_path):
    import hashlib
    path = make_image(tmp_path / "test.png")
    before = path.read_bytes()
    def handler(_):
        path.write_bytes(b"changed during request")
        return httpx.Response(200, json=response())
    model = Workspace().extract(str(path), client=client(handler))
    assert model.provenance["sha256"] == hashlib.sha256(before).hexdigest()


def test_transparent_background_composited_on_white(tmp_path):
    path = tmp_path / "transparent.png"
    image = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    image.putpixel((25, 25), (0, 0, 0, 255))
    image.save(path)
    page = list(render_pages(path))[0][1]
    with Image.open(io.BytesIO(page)) as rendered:
        assert rendered.getpixel((0, 0)) == (255, 255, 255)
        assert rendered.getpixel((25, 25)) == (0, 0, 0)


def test_published_extraction_schema_matches_runtime():
    schema_path = Path(__file__).parents[1] / "schemas" / "page-extraction.schema.json"
    assert json.loads(schema_path.read_text()) == PageExtraction.model_json_schema()
