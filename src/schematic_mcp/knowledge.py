"""Local, provenance-preserving component knowledge; never fetches URLs implicitly."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pypdfium2 as pdfium

from schematic_mcp.models import Component, Schematic

MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_BYTES = 100 * 1024 * 1024
MPN_FIELDS = ("MPN", "Mfr Part #", "Manufacturer Part Number", "Manufacturer_Part_Number")
MAKER_FIELDS = ("Manufacturer", "Mfr", "Manufacturer Name")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def _within(path: Path, root: Path | None) -> Path:
    resolved = path.resolve()
    if root and resolved != root and root not in resolved.parents:
        raise PermissionError(f"Knowledge document is outside SCHEMATIC_MCP_ROOT ({root})")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate knowledge JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON number: {value}")


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    path: str
    sha256: str
    revision: str
    url: str | None


@dataclass(frozen=True, slots=True)
class Fact:
    id: str
    name: str
    value: str
    document_id: str
    page: int
    locator: str
    quote: str | None
    status: str


@dataclass(frozen=True, slots=True)
class Part:
    manufacturer: str
    mpn: str
    documents: tuple[Document, ...]
    facts: tuple[Fact, ...]

    @property
    def id(self) -> str:
        return f"{self.manufacturer}:{self.mpn}"


class KnowledgeBase:
    def __init__(self, path: Path, parts: tuple[Part, ...], sha256: str, root: Path | None):
        self.path, self.parts, self.sha256, self.root = path, parts, sha256, root
        self._by_mpn: dict[str, list[Part]] = {}
        for part in parts:
            self._by_mpn.setdefault(part.mpn.casefold(), []).append(part)

    @classmethod
    def load(cls, path: Path, root: Path | None = None) -> "KnowledgeBase":
        root = root.resolve() if root else None
        path = _within(path, root)
        if not path.is_file() or path.suffix.lower() != ".json":
            raise ValueError("Knowledge manifest must be an existing .json file")
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError("Knowledge manifest exceeds 8 MiB")
        raw = path.read_bytes()
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        if not isinstance(data, dict) or data.get("schema_version") != "1.0" or not isinstance(data.get("parts"), list):
            raise ValueError("Expected knowledge schema_version 1.0 with parts list")
        parts = []
        seen_parts: set[tuple[str, str]] = set()
        for entry in data["parts"]:
            if not isinstance(entry, dict):
                raise ValueError("Part must be an object")
            manufacturer = _string(entry.get("manufacturer"), "manufacturer")
            mpn = _string(entry.get("mpn"), "mpn")
            key = (manufacturer.casefold(), mpn.casefold())
            if key in seen_parts:
                raise ValueError(f"Duplicate knowledge part: {manufacturer}:{mpn}")
            seen_parts.add(key)
            if not isinstance(entry.get("documents"), list) or not isinstance(entry.get("facts"), list):
                raise ValueError("Part requires documents and facts lists")
            documents = []
            doc_ids = set()
            page_counts = {}
            for item in entry["documents"]:
                if not isinstance(item, dict):
                    raise ValueError("Document must be an object")
                doc_id = _string(item.get("id"), "document id")
                if doc_id in doc_ids:
                    raise ValueError(f"Duplicate document id: {doc_id}")
                doc_ids.add(doc_id)
                relative = Path(_string(item.get("path"), "document path"))
                if relative.is_absolute():
                    raise ValueError("Knowledge document path must be relative to the manifest")
                document_path = _within(path.parent / relative, root)
                if not document_path.is_file() or document_path.suffix.lower() != ".pdf":
                    raise ValueError(f"Knowledge document must be an existing PDF: {relative}")
                if document_path.stat().st_size > MAX_DOCUMENT_BYTES:
                    raise ValueError(f"Knowledge document exceeds 100 MiB: {relative}")
                expected = _string(item.get("sha256"), "document sha256").lower()
                if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
                    raise ValueError("Document sha256 must be a 64-character hex digest")
                if _sha256(document_path) != expected:
                    raise ValueError(f"Knowledge document hash mismatch: {relative}")
                try:
                    pdf = pdfium.PdfDocument(str(document_path))
                    page_counts[doc_id] = len(pdf)
                    pdf.close()
                except Exception as exc:
                    raise ValueError(f"Knowledge document is not a readable PDF: {relative}") from exc
                url = item.get("url")
                if url is not None and (not isinstance(url, str) or urlparse(url).scheme != "https"
                                        or not urlparse(url).hostname or urlparse(url).username):
                    raise ValueError("Document URL must be an HTTPS URL without credentials")
                documents.append(Document(doc_id, _string(item.get("title"), "document title"),
                                          relative.as_posix(), expected,
                                          _string(item.get("revision"), "document revision"), url))
            facts = []
            fact_ids = set()
            for item in entry["facts"]:
                if not isinstance(item, dict):
                    raise ValueError("Fact must be an object")
                fact_id = _string(item.get("id"), "fact id")
                if fact_id in fact_ids:
                    raise ValueError(f"Duplicate fact id: {fact_id}")
                fact_ids.add(fact_id)
                document_id = _string(item.get("document_id"), "fact document_id")
                if document_id not in doc_ids:
                    raise ValueError(f"Fact {fact_id} cites an unknown document")
                page = item.get("page")
                if type(page) is not int or not 1 <= page <= page_counts[document_id]:
                    raise ValueError(f"Fact {fact_id} needs an existing one-based PDF page")
                quote = item.get("quote")
                if quote is not None:
                    quote = _string(quote, "fact quote")
                    document_path = _within(path.parent / next(d.path for d in documents if d.id == document_id), root)
                    pdf = pdfium.PdfDocument(str(document_path))
                    try:
                        pdf_page = pdf[page - 1]
                        textpage = pdf_page.get_textpage()
                        page_text = textpage.get_text_range()
                        textpage.close()
                        pdf_page.close()
                    finally:
                        pdf.close()
                    normalize = lambda value: " ".join(value.casefold().split())
                    value = _string(item.get("value"), "fact value")
                    if normalize(quote) not in normalize(page_text) or normalize(value) not in normalize(quote):
                        raise ValueError(f"Fact {fact_id} quote is absent from cited PDF page")
                facts.append(Fact(fact_id, _string(item.get("name"), "fact name"),
                                  _string(item.get("value"), "fact value"), document_id, page,
                                  _string(item.get("locator"), "fact locator"), quote,
                                  "quote_located" if quote else "page_cited_unverified"))
            parts.append(Part(manufacturer, mpn, tuple(documents), tuple(facts)))
        knowledge = cls(path, tuple(parts), hashlib.sha256(raw).hexdigest(), root)
        knowledge.verify()
        return knowledge

    def verify(self) -> None:
        if _sha256(self.path) != self.sha256:
            raise ValueError("Knowledge manifest changed after loading")
        checked = set()
        for part in self.parts:
            for document in part.documents:
                path = _within(self.path.parent / document.path, self.root)
                key = (path, document.sha256)
                if key in checked:
                    continue
                if not path.is_file() or path.stat().st_size > MAX_DOCUMENT_BYTES or _sha256(path) != document.sha256:
                    raise ValueError(f"Knowledge document changed after loading: {document.path}")
                checked.add(key)

    def match(self, component: Component) -> tuple[Part | None, str]:
        mpns = {component.properties[key].strip() for key in MPN_FIELDS
                if component.properties.get(key, "").strip()}
        if not mpns:
            return None, "missing_mpn"
        if len({value.casefold() for value in mpns}) != 1:
            return None, "conflicting_mpn_fields"
        mpn = next(iter(mpns))
        candidates = self._by_mpn.get(mpn.casefold(), [])
        makers = {component.properties[key].strip() for key in MAKER_FIELDS
                  if component.properties.get(key, "").strip()}
        if len({value.casefold() for value in makers}) > 1:
            return None, "conflicting_manufacturer_fields"
        if makers:
            maker = next(iter(makers))
            candidates = [part for part in candidates if part.manufacturer.casefold() == maker.casefold()]
        if len(candidates) != 1:
            return None, "ambiguous_mpn" if len(candidates) > 1 else "not_found"
        return candidates[0], "matched"

    def context(self, model: Schematic) -> dict:
        self.verify()
        matched = []
        unresolved: dict[str, list[str]] = {}
        reference_counts = Counter(c.reference for c in model.components)
        for component in model.components:
            if reference_counts[component.reference] != 1:
                unresolved.setdefault("ambiguous_reference", []).append(component.reference)
                continue
            part, status = self.match(component)
            if part is None:
                unresolved.setdefault(status, []).append(component.reference)
                continue
            matched.append({"reference": component.reference, "manufacturer": part.manufacturer,
                            "mpn": part.mpn, "part_id": part.id,
                            "documents": [asdict(doc) for doc in part.documents],
                            "facts": [{**asdict(fact), "citation_id": f"{component.reference}/{fact.id}"}
                                      for fact in part.facts]})
        return {"schema_version": "1.0", "manifest_sha256": self.sha256, "matched": matched,
                "unresolved": unresolved, "coverage": {"matched": len(matched),
                                                       "total": len(model.components)}}
