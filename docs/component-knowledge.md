# Component knowledge and evidence

The electrical graph and the component knowledge base are two inputs to review. The graph answers *which physical pins share a net*; the knowledge base answers *what the exact purchased part's documents say*. The review application combines them without treating a symbol value or a search hit as a confirmed manufacturer part number.

## Source policy

1. Use customer-supplied BOM/MPN fields and authorized datasheets first. Keep customer files local and out of the repository and public demos.
2. Public manufacturer or distributor pages can help discover candidates, but a link is not a verified fact. Check manufacturer, complete MPN, PDF revision, page and source rights before adding it to the local manifest. No tool in this release downloads a URL or sends a PDF to a model implicitly.
3. Store only a small, curated fact with a precise PDF citation. The PDF stays in its original location. A pinned SHA-256 guards against silent changes. `quote_located` means a quoted string was found on the cited PDF page; it does **not** prove the electrical interpretation. A page-only fact is marked `page_cited_unverified`.
4. If MPN or manufacturer cannot be matched exactly, the component is unresolved. The reviewer must request the BOM or datasheet instead of guessing from a generic KiCad symbol or similar product.

The manifest is a local JSON file with schema version `1.0`. For each part, provide manufacturer, MPN, PDF documents, and optionally facts. Each document needs an ID, title, path relative to the manifest, SHA-256 and revision. HTTPS URL is optional metadata and is never fetched automatically. Each fact needs an ID, name, value, document ID, one-based PDF page and locator. A `quote` is optional, but when present the loader checks that both the quote and fact value appear in text extracted from the cited PDF page. Scanned/image-only PDFs can use page-only citations, which remain unverified.

```json
{
  "schema_version": "1.0",
  "parts": [{
    "manufacturer": "Example Semi",
    "mpn": "X100",
    "documents": [{
      "id": "demo-ds", "title": "Synthetic X100 datasheet",
      "path": "demo-device.pdf", "sha256": "<64 hexadecimal characters>",
      "revision": "1.0"
    }],
    "facts": [{
      "id": "vin-max", "name": "Maximum input voltage", "value": "3.6 V",
      "document_id": "demo-ds", "page": 1, "locator": "Electrical limits",
      "quote": "Maximum input voltage 3.6 V"
    }]
  }]
}
```

The repository contains this **synthetic** example in `examples/knowledge/`. It describes no real commercial device. `examples/minimal.kicad_sch` has an example `MPN` and `Manufacturer` field on `U1`. The resolver accepts exact MPN fields named `MPN`, `Mfr Part #`, `Manufacturer Part Number`, or `Manufacturer_Part_Number`, and manufacturer fields named `Manufacturer`, `Mfr`, or `Manufacturer Name`. If manufacturer is absent, the MPN must be unique in the manifest. The symbol `Value` is never promoted to an MPN.

```bash
schematic-review examples/minimal.kicad_sch \
  --knowledge examples/knowledge/components.json --output ./knowledge-review
schematic-reader examples/minimal.kicad_sch \
  --knowledge examples/knowledge/components.json --output ./knowledge-reader.html
```

In MCP, call `load_component_knowledge(path)`, then `component_knowledge(reference)` or `review_schematic()`. With `--root` or `SCHEMATIC_MCP_ROOT`, the manifest and every linked PDF must stay inside that root, including resolved symlinks. Loading a new manifest is atomic; a failed load leaves the previous one in place. The manifest and documents are rehashed when knowledge is used. Reader and report artifacts include fact text and source metadata, so treat them as confidential whenever the input is confidential.

## BOM identity when the schematic has no MPN

`schematic-review` writes `bom-template.csv` beside `model.json` for native KiCad files. Fill exact `Manufacturer` and `MPN` values for the references you know, and delete rows whose identity is unknown. Keep the `Project SHA256` column unchanged. It fingerprints the root and every child sheet, so a BOM from another revision is rejected. The CSV is UTF-8 with exactly these columns, in this order:

```csv
Reference,Manufacturer,MPN,Project SHA256
U1,Example Semi,X100,<fingerprint copied from bom-template.csv>
```

The example above is illustrative; the angle-bracket text is not a valid fingerprint. To create a real BOM, run `schematic-review examples/minimal.kicad_sch --output ./first-review`, edit `first-review/bom-template.csv`, then run:

```sh
schematic-review examples/minimal.kicad_sch --knowledge examples/knowledge/components.json --bom first-review/bom-template.csv --output ./review-with-bom
schematic-reader examples/minimal.kicad_sch --knowledge examples/knowledge/components.json --bom first-review/bom-template.csv --output ./reader-with-bom.html
```

Fill or remove every blank row before loading. BOM references must occur exactly once in the schematic. If an MPN or manufacturer in a symbol disagrees with the BOM, that reference is unresolved and no datasheet fact is attached. The CSV, project and PDFs are rechecked when evidence is used. Imported JSON and vision extraction cannot accept this source-bound BOM. In MCP, open the native schematic/project, call `load_component_bom(path)` and `load_component_knowledge(path)`, then query `component_knowledge(reference)` or review. The BOM supplies part identity, not evidence for an electrical rating; the pinned document and page still supply that evidence. Do not commit private BOMs to this repository.

An optional LLM review receives only the matched, cited knowledge records alongside the electrical graph. A model finding that uses a knowledge fact must cite an exact `reference/fact-id`; invalid or unrelated citations are rejected. This is a hypothesis for an engineer to check, not a design sign-off. Current deterministic rules remain limited to graph-derived checks and do not turn a transcribed PDF limit into an automatic pass/fail verdict.

## Next data integrations

An online provider should be an explicit, replaceable discovery adapter, with response cache, rate limits, license/terms review, provenance and per-field trust status. Manufacturer documents should take priority over distributor catalog attributes when they disagree. Do not build a scraped global PDF corpus or redistribute customer documents in the open-source repository.
