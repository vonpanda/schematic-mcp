# Architecture

`schematic-mcp` separates **file parsing** from **agent-facing semantics**.

```text
MCP host / AI agent
        |
        | Model Context Protocol
        v
+-----------------------+
| schematic_mcp.server  |
+-----------+-----------+
            |
            v
+-----------------------+
| Workspace + Graph API |
+-----------+-----------+
            |
            v
+-----------------------+
| Canonical model       |
| Component / Pin / Net |
+-----------+-----------+
            ^
            |
+-----------+-----------+
| Format adapters       |
| V0.1: KiCad           |
+-----------------------+
```

## Design rules

1. **Deterministic first.** Structured EDA formats are parsed directly rather than sent through an LLM.
2. **No invented connectivity.** A trace follows resolved electrical nets only.
3. **Format adapters are isolated.** Future PDF, Altium and EasyEDA adapters feed the same canonical model.
4. **Filesystem access is explicit.** `SCHEMATIC_MCP_ROOT` can constrain agent-visible files to one directory tree.
5. **Warnings are data.** Ambiguous or partially supported structures are surfaced instead of silently guessed.

The offline KiCad S-expression parser covers the root sheet. The optional KiCad CLI XML-netlist adapter supplies source-resolved cross-sheet connectivity for full projects; it uses the same canonical model and graph/MCP queries. The standalone reader uses KiCad's SVG export for artwork and shows KiCad ERC separately from this project's rules.

## V0.1 scope

- Modern KiCad `.kicad_sch` files
- Component reference/value/library ID
- Library pin geometry and symbol transforms
- Wire/label/junction connectivity
- Named and anonymous nets
- Net-based signal tracing
- Child sheet references
- MCP tools and resources

## Planned adapters

- PDF/vector schematic reconstruction with confidence metadata
- Altium schematic export/API adapter
- EasyEDA / LCSC schematic adapter
- Datasheet context
- Firmware pin-map cross-checking
- PCB/BOM/Gerber context

## Opt-in confidence-based adapter and review

`parsers/vision.py` renders bounded PDF/image snapshots and sends page overview/detail images through `llm.py` to a configured Chat Completions-compatible vision provider. `vision_schema.py` validates both JSON and graph integrity before canonical conversion. Every component/pin/net observation keeps source evidence. The adapter preserves page scope and explicit ambiguity and never labels its output source-resolved.

`models.py` carries provenance and exposes a connectivity status. `graph.py` propagates that status and disallows successful firmware-pin validation on unverified data. `model_io.py` supports graph-validated offline JSON reload without trusting imported provenance claims. `Workspace` publishes a model/graph pair atomically only after successful parsing, retaining the old state on failure.

`review.py` runs deterministic electrical rules and optional separately requested LLM hypotheses. Findings carry source-linked endpoints and coverage limitations; no report grants design approval. `cli.py` provides model/report exports independently of MCP. Read [vision and review](vision-and-review.md) for the schema, deployment boundaries and real-model validation gate.
