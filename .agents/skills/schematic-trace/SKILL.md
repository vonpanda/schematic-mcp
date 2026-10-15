---
name: schematic-trace
description: Trace a signal, MCU pin, component, or net through the schematic-mcp electrical graph with source-aware uncertainty. Use for connection questions, firmware pin contracts, and suspected miswires.
---

# Trace electrical connectivity

1. Open the native file or explicitly authorized extracted model, then inspect schematic_summary and connectivity_status. For cross-sheet paths, use open_schematic_project so the whole KiCad XML netlist is represented.
2. Resolve the requested component with get_component and exact physical pin with get_pin. Use trace_signal and get_net to list all represented endpoints. For a broad MCU query, use get_mcu_pinmap; compare an explicit firmware contract with validate_pinmap.
3. Distinguish exact pin numbers, symbolic names, net labels and anonymous net IDs. KiCad's full-project netlist can prefix local names with their sheet path (for example /SENSOR_OUT on the root); preserve the exact exported name in comparisons. If a duplicate reference, pin name or label is ambiguous, show both candidates and do not merge them.
4. Trace only drawn nets. Internal IC paths, off-page hierarchy not loaded into the graph, and vision-inferred wires are outside a verified trace. A source-resolved native trace establishes what this parser read, not electrical correctness of the board.
5. Return a compact path table: starting pin, resolved net, every represented endpoint, source/position or page evidence, and any coverage warning. Quote the relevant source warning when a trace stops early.

When validating firmware, report matches, mismatches, unresolved and unverified separately. Never turn an unverified result into a pass.
