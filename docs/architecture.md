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
