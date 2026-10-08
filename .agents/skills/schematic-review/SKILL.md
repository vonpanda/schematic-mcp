---
name: schematic-review
description: Review a hardware schematic for actionable electrical risks using deterministic checks, source-linked findings, and explicit missing evidence. Use when an engineer asks for ERC, design review, defect triage, or a review report.
---

# Evidence-based schematic review

1. Start with schematic-intake when the input has not yet been opened. Confirm source hash, represented pages/sheets, warnings and connectivity_status.
2. Run review_schematic for deterministic candidate findings. Use KiCad's own ERC as a separate cross-check when the project and kicad-cli are available; do not treat one tool's silence as the other's pass. Run review_schematic_with_llm only when external model review is explicitly authorized.
3. For each finding, inspect the original drawing in schematic-reader and its exact endpoint/net evidence. Classify it as confirmed source observation, plausible hypothesis, false positive, or blocked by missing evidence. Keep that classification separate from severity.
4. Before making quantitative power, timing, polarity, decoupling or component-limit claims, obtain the exact datasheet revision, BOM part, supply assumptions and applicable sheet. Without them, state the missing evidence and a concrete check rather than guessing values.
5. Deliver a report ordered by potential impact. Each actionable row needs: source location, rule or mechanism, affected endpoints, observed fact, inference, verification step, and recommended change. Include unresolved warnings, unreviewed sheets and a clear needs_engineering_review status.

Do not claim design sign-off, expert-labeled accuracy, or a defect rate from synthetic fixtures. Recheck any changed drawing from the source and compare the same endpoints again.
