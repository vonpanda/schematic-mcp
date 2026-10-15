"""Explicit, source-bound CSV BOM assignments for native KiCad schematics."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path

from schematic_mcp.models import Schematic

MAX_BOM_BYTES = 8 * 1024 * 1024
FIELDS = ("Reference", "Manufacturer", "MPN", "Project SHA256")


def project_fingerprint(source: Path, hashes: dict[Path, str]) -> str:
    """Stable across checkout locations; changes if any source sheet changes."""
    base = source.parent.resolve()
    pairs = sorted((Path(os.path.relpath(path.resolve(), base)).as_posix(), digest)
                   for path, digest in hashes.items())
    return hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()


def template(model: Schematic) -> str:
    """A fillable export with the exact project fingerprint and symbol hints."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(FIELDS)
    fingerprint = model.provenance.get("project_sha256", "")
    for component in sorted(model.components, key=lambda item: item.reference):
        writer.writerow([component.reference, component.properties.get("Manufacturer", ""),
                         component.properties.get("MPN", ""), fingerprint])
    return output.getvalue()


@dataclass(frozen=True, slots=True)
class Assignment:
    manufacturer: str
    mpn: str


class Bom:
    def __init__(self, path: Path, sha256: str, project_sha256: str,
                 assignments: dict[str, Assignment], root: Path | None):
        self.path, self.sha256, self.project_sha256 = path, sha256, project_sha256
        self.assignments, self.root = assignments, root

    @classmethod
    def load(cls, path: Path, model: Schematic, root: Path | None = None) -> "Bom":
        path = path.resolve()
        root = root.resolve() if root else None
        if root and path != root and root not in path.parents:
            raise PermissionError(f"BOM is outside SCHEMATIC_MCP_ROOT ({root})")
        if not path.is_file() or path.suffix.lower() != ".csv":
            raise ValueError("BOM must be an existing .csv file")
        if model.provenance.get("method") not in {"native_parser", "kicad_cli_netlist"}:
            raise ValueError("BOM binding requires a native KiCad schematic, not imported or vision data")
        if model.sheets and not model.provenance.get("hierarchy_complete"):
            raise ValueError("BOM binding requires the complete KiCad hierarchy; open the project with KiCad CLI")
        expected = model.provenance.get("project_sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("Native schematic has no project fingerprint")
        with path.open("rb") as stream:
            raw = stream.read(MAX_BOM_BYTES + 1)
        if len(raw) > MAX_BOM_BYTES:
            raise ValueError("BOM exceeds 8 MiB")
        try:
            decoded = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("BOM must be UTF-8 CSV") from exc
        try:
            reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
            if reader.fieldnames != list(FIELDS):
                raise ValueError("BOM columns must be Reference,Manufacturer,MPN,Project SHA256")
            refs = {component.reference.casefold() for component in model.components}
            if len(refs) != len(model.components):
                raise ValueError("Schematic has ambiguous duplicate references")
            assignments = {}
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("BOM row has the wrong number of fields")
                values = {key: value.strip() for key, value in row.items()}
                if any(not value for value in values.values()):
                    raise ValueError("BOM fields must not be blank")
                reference = values["Reference"]
                if reference.casefold() not in refs:
                    raise ValueError(f"BOM reference absent from schematic: {reference}")
                if reference.casefold() in assignments:
                    raise ValueError(f"Duplicate BOM reference: {reference}")
                if values["Project SHA256"] != expected:
                    raise ValueError("BOM project fingerprint does not match the loaded schematic")
                assignments[reference.casefold()] = Assignment(values["Manufacturer"], values["MPN"])
        except csv.Error as exc:
            raise ValueError("Malformed BOM CSV") from exc
        if not assignments:
            raise ValueError("BOM has no assignments")
        result = cls(path, hashlib.sha256(raw).hexdigest(), expected, assignments, root)
        result.verify(model)
        return result

    def verify(self, model: Schematic) -> None:
        if model.provenance.get("method") not in {"native_parser", "kicad_cli_netlist"} or (model.sheets and not model.provenance.get("hierarchy_complete")):
            raise ValueError("BOM binding requires a source-resolved complete KiCad model")
        if model.provenance.get("project_sha256") != self.project_sha256:
            raise ValueError("BOM belongs to a different schematic version")
        path = self.path.resolve()
        if self.root and path != self.root and self.root not in path.parents:
            raise PermissionError("BOM moved outside SCHEMATIC_MCP_ROOT")
        if not path.is_file() or path.stat().st_size > MAX_BOM_BYTES or hashlib.sha256(path.read_bytes()).hexdigest() != self.sha256:
            raise ValueError("BOM changed after loading")
        sheet_hashes = model.provenance.get("sheet_sha256") or {model.path: model.provenance.get("sha256")}
        for source, expected in sheet_hashes.items():
            path = Path(source)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Schematic source changed after BOM binding")
