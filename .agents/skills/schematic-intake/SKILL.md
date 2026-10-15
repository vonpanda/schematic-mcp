---
name: schematic-intake
description: Open a KiCad schematic or opt-in PDF/image extraction for hardware review, assess source coverage and trust, and prepare a navigable reader. Use when an engineer gives a new drawing or asks what the project contains.
---

# Schematic intake

1. Establish the authorized project root and input format. Use open_schematic for pure file parsing of a KiCad root sheet, or open_schematic_project for a complete KiCad hierarchy when KiCad CLI is installed. For PDF/images, explain that extraction sends pages to the configured vision provider and only call extract_schematic or schematic-reader --vision when that transmission is authorized.
2. Open the source with the appropriate tool. Read schematic_summary, warnings, provenance, connectivity_status and child sheet count before claiming coverage.
3. Produce an offline reader with schematic-reader when the engineer needs to navigate the actual drawing. For native KiCad, this uses KiCad CLI only to draw SVG; electrical facts still come from the parser. Keep the original source and its SHA-256 associated with the review.
4. Record which pages/sheets are covered, unreadable, excluded or unexpanded. If using open_schematic on a root with child sheets, say that its graph omits their connectivity; use open_schematic_project when a full graph is needed. Imported JSON and vision graphs remain unverified even if a report has no findings.
5. Hand the engineer a short inventory of components, nets, unresolved pins and warnings, followed by the exact scope of the next review. Do not label a drawing approved based on extraction.

Relevant CLI: schematic-reader INPUT --output NEW.html; schematic-review INPUT --output NEW_DIR. See docs/reader-and-skills.md for setup and format limits.
