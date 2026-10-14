import hashlib
import json
from pathlib import Path

import pytest

from schematic_mcp.knowledge import KnowledgeBase
from schematic_mcp.models import Component, Pin, Schematic
from schematic_mcp.review import review_schematic
from schematic_mcp.review import SuggestedReview
from schematic_mcp.llm import LLMError


def pdf_fixture(path: Path):
    stream = b"BT /F1 12 Tf 72 720 Td (Maximum input voltage 3.6 V) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)


def manifest(tmp_path: Path):
    document = tmp_path / "device.pdf"
    pdf_fixture(document)
    data = {"schema_version": "1.0", "parts": [{"manufacturer": "Example Semi", "mpn": "X100",
        "documents": [{"id": "ds", "title": "X100 datasheet", "path": "device.pdf",
                       "sha256": hashlib.sha256(document.read_bytes()).hexdigest(), "revision": "1.0"}],
        "facts": [{"id": "vin-max", "name": "Maximum input voltage", "value": "3.6 V",
                   "document_id": "ds", "page": 1, "locator": "Electrical limits",
                   "quote": "Maximum input voltage 3.6 V"}]}]}
    path = tmp_path / "knowledge.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def model(mpn="X100", manufacturer="Example Semi"):
    return Schematic(path="test.kicad_sch", format="kicad_sch", components=[
        Component(reference="U1", value="X100", lib_id="Example:U", properties={"MPN": mpn,
                  "Manufacturer": manufacturer}, pins=[Pin(number="1", electrical_type="input")])])


def test_knowledge_matches_exact_mpn_and_cites_pinned_pdf(tmp_path):
    path, _ = manifest(tmp_path)
    kb = KnowledgeBase.load(path, tmp_path)
    context = kb.context(model())
    assert context["coverage"] == {"matched": 1, "total": 1}
    assert context["matched"][0]["facts"][0]["citation_id"] == "U1/vin-max"
    assert context["matched"][0]["facts"][0]["status"] == "quote_located"
    report = review_schematic(model(), knowledge=kb)
    assert report["coverage"]["knowledge"] == {"matched": 1, "total": 1}
    assert report["status"] == "needs_engineering_review"
    assert kb.context(model(mpn="X100A"))["coverage"]["matched"] == 0
    assert kb.context(model(manufacturer="Other"))["coverage"]["matched"] == 0
    conflicting = model()
    conflicting.components[0].properties["Mfr Part #"] = "X100A"
    assert kb.context(conflicting)["unresolved"] == {"conflicting_mpn_fields": ["U1"]}


@pytest.mark.parametrize("change,error", [
    (lambda d: d["parts"][0]["facts"][0].update(page=2), "existing one-based"),
    (lambda d: d["parts"][0]["facts"][0].update(quote="5.0 V"), "quote is absent"),
    (lambda d: d["parts"][0]["facts"][0].update(value="5.0 V"), "quote is absent"),
    (lambda d: d["parts"][0]["documents"][0].update(sha256="0" * 64), "hash mismatch"),
    (lambda d: d["parts"][0]["documents"][0].update(url="file:///secret"), "HTTPS URL"),
])
def test_knowledge_rejects_bad_evidence(tmp_path, change, error):
    path, data = manifest(tmp_path)
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        KnowledgeBase.load(path, tmp_path)


def test_knowledge_rejects_symlink_outside_root(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    path, data = manifest(tmp_path)
    (allowed / "device.pdf").symlink_to(tmp_path / "device.pdf")
    inside = allowed / "knowledge.json"
    inside.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PermissionError, match="outside"):
        KnowledgeBase.load(inside, allowed)


def test_knowledge_rechecks_document_and_rejects_ambiguous_reference(tmp_path):
    path, _ = manifest(tmp_path)
    kb = KnowledgeBase.load(path, tmp_path)
    duplicate = model()
    duplicate.components.append(duplicate.components[0])
    context = kb.context(duplicate)
    assert context["coverage"]["matched"] == 0
    assert context["unresolved"]["ambiguous_reference"] == ["U1", "U1"]
    (tmp_path / "device.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed after loading"):
        kb.context(model())


def test_knowledge_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "knowledge.json"
    path.write_text('{"schema_version":"1.0","parts":[],"parts":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate knowledge JSON key"):
        KnowledgeBase.load(path, tmp_path)


@pytest.mark.parametrize("citation,accepted", [("U1/vin-max", True), ("U2/vin-max", False),
                                                  ("U1/made-up", False)])
def test_llm_knowledge_citations_must_belong_to_cited_component(tmp_path, citation, accepted):
    path, _ = manifest(tmp_path)
    kb = KnowledgeBase.load(path, tmp_path)

    class Reviewer:
        def request(self, *_):
            return SuggestedReview.model_validate({"findings": [{"severity": "warning", "title": "Review voltage",
                "explanation": "A cited limit may apply", "endpoints": ["U1.1"],
                "recommendation": "Verify the actual rail", "missing_information": [],
                "knowledge_sources": [citation]}], "limitations": []})

    if accepted:
        report = review_schematic(model(), Reviewer(), kb)
        assert report["findings"][-1]["knowledge_sources"] == [citation]
    else:
        with pytest.raises(LLMError, match="knowledge facts"):
            review_schematic(model(), Reviewer(), kb)
