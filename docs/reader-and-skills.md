# Schematic reader and agent skills

The reader is a portable, read-only HTML view of the original drawing alongside the repository's component/pin/net model and evidence-linked review. It can search components, nets and findings; switch pages; zoom; and highlight represented source positions. It is intended for engineer inspection, not design approval.

## Native KiCad

Install the project and KiCad. KiCad's official CLI renders the artwork; schematic-mcp parses electrical data independently:

    python -m pip install -e '.[dev]'
    schematic-reader board.kicad_sch --output board-review.html

On macOS the reader also discovers /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli. Use --kicad-cli PATH or SCHEMATIC_KICAD_CLI for another installation. Open the generated HTML file locally in a browser. It embeds all pages and data, has a restrictive content-security policy, and makes no background network request. Treat the file as containing the full drawing: distribute it only to authorized reviewers.

For a multi-sheet project, the reader preflights child-sheet paths, uses KiCad's XML netlist export for the complete electrical graph, and attaches positions from native sheets where matching symbols are unambiguous. It checks the root and child-sheet hashes again before publishing. KiCad CLI draws the pages and runs its own ERC as a separate cross-check. KiCad ERC results are shown on their own tab rather than merged with this project's rules. KiCad ERC locations are shown as reported text until coordinate mapping is verified.

The MCP tool open_schematic still uses the offline root-sheet parser. Use open_schematic_project or schematic-review --project for full-hierarchy KiCad queries and reports; these require the installed KiCad CLI. The project graph is derived from KiCad's own netlist and marked with that provenance. A source-resolved graph means the exported file's connectivity was read, not that the design is correct.

Exact KiCad XML net names are preserved, including sheet-path prefixes such as /SENSOR_OUT. Pin-map contracts for the full-project mode should use those names, or explicitly map project names in the calling workflow; the library does not silently strip a prefix that could distinguish two nets.

## PDF and images

PDF/PNG/JPEG/WebP extraction requires the optional vision dependencies and an explicitly configured provider. This sends selected drawing pages to that provider:

    python -m pip install -e '.[vision]'
    schematic-reader drawing.pdf --vision --output drawing-review.html
    schematic-reader drawing.pdf --vision --pages 2 3 --output selected-review.html

Use --llm-review only for separately authorized model hypotheses. See [vision and review](vision-and-review.md) for provider configuration, privacy, extraction schema and accuracy boundaries. Image evidence boxes are visual pointers, not proof that the model read a wire correctly. Imported and vision-derived connectivity stays unverified.

Both modes respect --root for source reads and refuse to replace an existing HTML output. The source hash is checked again after rendering to catch drawings changed mid-review. The bundle has an 80 MiB limit; oversized sources require selected pages or separate reviews. A successful command means the reader was generated, not that a circuit passed review.

## Repo-local skills

Codex discovers the workflows in .agents/skills/ when working in this repository:

| Skill | Use |
| --- | --- |
| schematic-intake | Open a drawing, assess provenance/coverage and create a reader |
| schematic-trace | Answer exact pin/net questions and verify firmware pin contracts |
| schematic-review | Triage deterministic and optional model findings against the drawing and missing datasheets |

The MCP server provides facts and tool calls. Skills define the review sequence and the evidence boundary. They do not add new electrical parsing capabilities or make unverified extraction source-resolved.

## Release and quality gate

The first public release needs more than a passing synthetic test suite. Build a permissioned, redistributable acceptance set with at least: clean and dense KiCad sheets, hierarchy, crossings/junctions, repeated labels, multi-unit symbols, NC markers, a PDF/image scan, and known design defects. Have hardware engineers label component IDs, physical pins, net membership, defect presence and source locations. Measure coverage, false positives and false negatives per rule and per input format; retain document hashes, KiCad/provider versions, latency and cost. Do not describe the project as a complete or expert-equivalent schematic reviewer until these measured results support it.
