"""Create a portable, read-only schematic review workspace."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from importlib.resources import files

from schematic_mcp.llm import JSONClient, LLMConfig
from schematic_mcp.parsers.kicad import KiCadSchematicParser
from schematic_mcp.parsers.kicad_netlist import parse_kicad_netlist
from schematic_mcp.review import review_schematic
from schematic_mcp.workspace import Workspace

MAX_BUNDLE_BYTES = 80 * 1024 * 1024


def _kicad_cli(explicit: str | None) -> str:
    candidate = explicit or os.environ.get("SCHEMATIC_KICAD_CLI") or shutil.which("kicad-cli")
    if not candidate and sys.platform == "darwin":
        candidate = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if not candidate or not Path(candidate).is_file():
        raise RuntimeError("KiCad CLI is required to render .kicad_sch; set --kicad-cli or SCHEMATIC_KICAD_CLI")
    return candidate


def _svg_page(path: Path) -> dict:
    raw = path.read_bytes()
    root = ET.fromstring(raw)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("KiCad export is not SVG")
    box = root.attrib.get("viewBox", "").replace(",", " ").split()
    if len(box) != 4:
        raise ValueError("KiCad SVG has no four-value viewBox")
    x, y, width, height = map(float, box)
    if width <= 0 or height <= 0 or not all(math.isfinite(v) for v in (x, y, width, height)):
        raise ValueError("KiCad SVG has invalid dimensions")
    return {"label": path.stem, "mime": "image/svg+xml", "image": base64.b64encode(raw).decode("ascii"),
            "box": [x, y, width, height]}


def _render_kicad(source: Path, cli: str) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="schematic-reader-") as temporary:
        output = Path(temporary)
        result = subprocess.run([cli, "sch", "export", "svg", "--output", str(output), str(source)],
                                capture_output=True, text=True, timeout=120, cwd=source.parent, check=False)
        if result.returncode:
            raise RuntimeError(f"KiCad SVG export failed (exit {result.returncode}): {result.stderr[-800:]}")
        paths = sorted(output.glob("*.svg"), key=lambda p: (p.stem != source.stem, p.name))
        if not paths:
            raise RuntimeError("KiCad SVG export produced no pages")
        return [_svg_page(path) for path in paths]


def _kicad_erc(source: Path, cli: str) -> dict:
    """Keep KiCad's ERC separate from schematic-mcp review findings."""
    with tempfile.TemporaryDirectory(prefix="schematic-erc-") as temporary:
        output = Path(temporary) / "erc.json"
        result = subprocess.run([cli, "sch", "erc", "--format", "json", "--output", str(output), str(source)],
                                capture_output=True, text=True, timeout=120, cwd=source.parent, check=False)
        if result.returncode or not output.is_file():
            return {"status": "unavailable", "message": f"KiCad ERC failed (exit {result.returncode})", "findings": []}
        if output.stat().st_size > 8 * 1024 * 1024:
            return {"status": "unavailable", "message": "KiCad ERC report exceeds 8 MiB", "findings": []}
        data = json.loads(output.read_text(encoding="utf-8"))
        findings = []
        for sheet in data.get("sheets", []):
            for violation in sheet.get("violations", []):
                findings.append({"id": f"ERC{len(findings)+1:03d}", "sheet": sheet.get("path", ""),
                                 "severity": violation.get("severity", ""),
                                 "type": violation.get("type", ""),
                                 "description": violation.get("description", ""),
                                 "items": violation.get("items", [])})
        return {"status": "complete", "kicad_version": data.get("kicad_version"),
                "ignored_checks": data.get("ignored_checks", []),
                "included_severities": data.get("included_severities", []),
                "findings": findings}


def _render_document(source: Path, pages: list[int] | None) -> list[dict]:
    from schematic_mcp.parsers.vision import render_pages
    return [{"label": f"Page {number}", "page": number, "mime": "image/png",
             "image": base64.b64encode(png).decode("ascii"), "box": [0, 0, 1, 1]}
            for number, png in render_pages(source, pages)]


def _project_sheets(source: Path, root: Path | None) -> dict[Path, object]:
    """Validate every source sheet before allowing KiCad to load the hierarchy."""
    found = {}
    pending = [source]
    parser = KiCadSchematicParser()
    while pending:
        path = pending.pop().resolve()
        if root and path != root and root not in path.parents:
            raise PermissionError(f"Child sheet is outside SCHEMATIC_MCP_ROOT ({root})")
        if path in found:
            continue
        if not path.is_file() or path.suffix.lower() != ".kicad_sch":
            raise FileNotFoundError(f"Missing KiCad child sheet: {path}")
        parsed = parser.parse(path)
        found[path] = parsed
        for sheet in parsed.sheets:
            if not sheet.file:
                raise ValueError(f"Child sheet has no filename in {path}")
            pending.append(path.parent / sheet.file)
    return found


def _project_model(source: Path, cli: str, root: Path | None) -> tuple[object, dict[Path, str]]:
    source_sheets = _project_sheets(source, root)
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_sheets}
    with tempfile.TemporaryDirectory(prefix="schematic-netlist-") as temporary:
        output = Path(temporary) / "netlist.xml"
        result = subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml",
                                 "--output", str(output), str(source)], capture_output=True, text=True,
                                timeout=120, cwd=source.parent, check=False)
        if result.returncode or not output.is_file():
            raise RuntimeError(f"KiCad project netlist export failed (exit {result.returncode})")
        if output.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("KiCad project netlist exceeds 32 MiB")
        model = parse_kicad_netlist(output.read_bytes(), source)
    known_filenames = {path.name for path in source_sheets}
    if any(not sheet.file or Path(sheet.file).name not in known_filenames for sheet in model.sheets):
        raise RuntimeError("KiCad netlist refers to a sheet not covered by source preflight")
    model.provenance.update({"sha256": hashes[source],
                             "sheet_sha256": {str(path): digest for path, digest in hashes.items()},
                             "hierarchy_complete": True})
    # Positions come from the native files; KiCad's exported netlist remains the
    # authority for cross-sheet pin-to-net membership.
    for component in model.components:
        sheetfile = component.properties.get("Sheetfile")
        path = (source.parent / sheetfile).resolve() if sheetfile else source
        parsed = source_sheets.get(path)
        if parsed is None:
            continue
        matches = [candidate for candidate in parsed.components if candidate.reference == component.reference]
        if not matches:
            continue
        component.position = matches[0].position
        for pin in component.pins:
            for candidate in matches:
                original = next((item for item in candidate.pins if item.number == pin.number), None)
                if original is not None:
                    pin.position = original.position
                    pin.evidence = {**(pin.evidence or {}), "path": str(path)}
                    break
        component.evidence = {**(component.evidence or {}), "path": str(path)}
    unplaced = sum(component.position is None for component in model.components)
    if unplaced:
        model.warnings.append(f"{unplaced} component placements could not be matched to SVG pages; connectivity is retained but visual location needs manual lookup.")
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
        raise RuntimeError("Project sheet changed during netlist export; retry")
    return model, hashes


def make_reader(source: str, output: Path, *, root: str | None = None, vision: bool = False,
                pages: list[int] | None = None, llm_review: bool = False,
                kicad_cli: str | None = None) -> dict:
    """Build one offline HTML file. Neither SVG export nor the browser supplies electrical facts."""
    if output.exists():
        raise FileExistsError(f"Reader output already exists: {output}")
    if output.suffix.lower() != ".html":
        raise ValueError("Reader output must have a .html extension")
    if pages and not vision:
        raise ValueError("--pages requires --vision")
    workspace = Workspace()
    if root:
        workspace.root = Path(root).expanduser().resolve()
    candidate = workspace._resolve(source)
    if vision:
        model = workspace.extract(source, pages)
        artwork = _render_document(candidate, pages)
        erc = {"status": "not_applicable", "findings": []}
    else:
        model = workspace.open(source)
        cli = _kicad_cli(kicad_cli)
        sheet_hashes = None
        if model.sheets:
            model, sheet_hashes = _project_model(candidate, cli, workspace.root)
        artwork = _render_kicad(candidate, cli)
        erc = _kicad_erc(candidate, cli)
        for page in artwork:
            for sheet in model.sheets:
                suffix = "-".join(part for part in sheet.name.split("/") if part)
                if page["label"] == candidate.stem + "-" + suffix:
                    page["sheet"] = sheet.name
                    break
            else:
                if page["label"] == candidate.stem:
                    page["sheet"] = "/"
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != model.provenance.get("sha256"):
        raise RuntimeError("Source changed between extraction and page rendering; retry from the updated drawing")
    if not vision and sheet_hashes and any(hashlib.sha256(path.read_bytes()).hexdigest() != digest
                                           for path, digest in sheet_hashes.items()):
        raise RuntimeError("Child sheet changed between extraction and page rendering; retry")
    # Finish all optional remote work before publishing an output file.
    report = review_schematic(model, JSONClient(LLMConfig.from_env()) if llm_review else None)
    payload = {"model": model.to_dict(), "report": report, "erc": erc, "pages": artwork}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    safe = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    safe = safe.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = files("schematic_mcp").joinpath("reader.html").read_text(encoding="utf-8").replace("__READER_DATA__", safe)
    if len(html.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise ValueError("Reader exceeds 80 MiB; review selected pages or split the document")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation keeps previously generated evidence immutable.
    with output.open("x", encoding="utf-8") as stream:
        stream.write(html)
    return {"output": str(output.resolve()), "pages": len(artwork), "summary": report["summary"],
            "kicad_erc": {"status": erc["status"], "findings": len(erc["findings"])},
            "connectivity_status": model.connectivity_status, "status": report["status"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an offline, interactive schematic reader")
    parser.add_argument("path", help="Native KiCad schematic, or PDF/PNG/JPEG/WebP with --vision")
    parser.add_argument("--output", required=True, type=Path, help="New .html file")
    parser.add_argument("--root", help="Restrict source reads to this directory")
    parser.add_argument("--vision", action="store_true", help="Send PDF/image to configured vision provider")
    parser.add_argument("--pages", type=int, nargs="+", help="One-based PDF pages")
    parser.add_argument("--llm-review", action="store_true", help="Send model to configured review provider")
    parser.add_argument("--kicad-cli", help="Path to the KiCad CLI renderer")
    args = parser.parse_args()
    try:
        result = make_reader(args.path, args.output, root=args.root, vision=args.vision,
                             pages=args.pages, llm_review=args.llm_review, kicad_cli=args.kicad_cli)
        print(json.dumps({"ok": True, **result}))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
