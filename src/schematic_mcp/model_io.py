"""Offline canonical JSON import with graph integrity and conservative trust."""
from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from schematic_mcp.models import Schematic


MAX_MODEL_BYTES = 8 * 1024 * 1024


def load_model(path: Path) -> Schematic:
    with path.open("rb") as source:
        raw = source.read(MAX_MODEL_BYTES + 1)
    if len(raw) > MAX_MODEL_BYTES:
        raise ValueError("Structured model exceeds 8 MiB")
    try:
        model = TypeAdapter(Schematic).validate_json(raw, strict=True)
    except ValidationError:
        raise ValueError("Invalid canonical model JSON") from None
    refs = [c.reference.upper() for c in model.components]
    if len(refs) != len(set(refs)) or any(not r or "." in r for r in refs):
        raise ValueError("Duplicate or invalid component reference")
    pins = {}
    for component in model.components:
        for pin in component.pins:
            endpoint = f"{component.reference}.{pin.number}"
            if not pin.number or "." in pin.number or endpoint in pins:
                raise ValueError("Duplicate or invalid physical pin")
            pins[endpoint] = pin
    names = [n.name for n in model.nets]
    if len(names) != len(set(names)) or any(not n for n in names):
        raise ValueError("Duplicate or empty net name")
    assigned = set()
    for net in model.nets:
        for endpoint in net.pins:
            if endpoint not in pins or endpoint in assigned or pins[endpoint].net != net.name:
                raise ValueError("Net endpoints and pin assignments are inconsistent")
            assigned.add(endpoint)
    if any(pin.net is not None and endpoint not in assigned for endpoint, pin in pins.items()):
        raise ValueError("Pin net assignment has no reciprocal net endpoint")
    # Editing a JSON file cannot manufacture native-parser trust. Preserve provenance
    # for inspection while marking all imported facts as unverified.
    model.provenance = {**model.provenance, "original_method": model.provenance.get("method"),
                        "method": "imported_json", "import_path": str(path),
                        "import_sha256": hashlib.sha256(raw).hexdigest()}
    model.warnings.append("Imported JSON is unverified, including claimed source provenance. Re-open the original native schematic to obtain source-resolved data.")
    return model
