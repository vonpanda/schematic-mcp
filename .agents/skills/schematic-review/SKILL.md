---
name: schematic-review
description: Review a hardware schematic for actionable electrical risks using deterministic checks, source-linked findings, and explicit missing evidence. Use when an engineer asks for ERC, design review, defect triage, or a review report.
---

# Evidence-based schematic review

1. Start with schematic-intake when the input has not yet been opened. Confirm source hash, represented pages/sheets, warnings and connectivity_status.
2. Run review_schematic for deterministic candidate findings. Use KiCad's own ERC as a separate cross-check when the project and kicad-cli are available; do not treat one tool's silence as the other's pass. Run review_schematic_with_llm only when external model review is explicitly authorized.
3. For each finding, inspect the original drawing in schematic-reader and its exact endpoint/net evidence. Classify it as confirmed source observation, plausible hypothesis, false positive, or blocked by missing evidence. Keep that classification separate from severity.
4. Before making quantitative power, timing, polarity, decoupling or component-limit claims, obtain the exact datasheet revision, BOM part, supply assumptions and applicable sheet. When MPN fields are absent, use the source-bound `bom-template.csv` from `schematic-review` and load a completed, authorized CSV with `load_component_bom`; reject stale project fingerprints and resolve any symbol/BOM conflicts with the engineer. If a local component manifest is available, call load_component_knowledge and check component_knowledge for the exact MPN, cited PDF page and fact status. Treat a located quote as text evidence that still needs engineering interpretation. Without these inputs, state the missing evidence and a concrete check rather than guessing values.
5. Deliver a report ordered by potential impact. Each actionable row needs: source location, rule or mechanism, affected endpoints, observed fact, inference, verification step, and recommended change. Include unresolved warnings, unreviewed sheets and a clear needs_engineering_review status.

Do not claim design sign-off, expert-labeled accuracy, or a defect rate from synthetic fixtures. Recheck any changed drawing from the source and compare the same endpoints again.
