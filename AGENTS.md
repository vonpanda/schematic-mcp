# AGENTS.md

This file gives coding agents and human contributors the project rules that matter most when changing `schematic-mcp`.

## Project goal

`schematic-mcp` is a hardware-context server for AI agents. It converts EDA schematics into a deterministic, format-neutral component/pin/net model and exposes that model through MCP.

The project is **not** trying to become a general-purpose KiCad GUI automation layer or an autorouter. The long-term direction is read-oriented hardware context, cross-EDA adapters, electrical reasoning, and firmware ↔ schematic validation.

## Architecture

- `src/schematic_mcp/parsers/` — EDA-specific adapters. New formats should terminate in the canonical model rather than leak format-specific behavior into MCP tools.
- `src/schematic_mcp/models.py` — canonical data structures.
- `src/schematic_mcp/graph.py` — deterministic graph/query helpers over the canonical model.
- `src/schematic_mcp/workspace.py` — current loaded schematic and filesystem boundary enforcement.
- `src/schematic_mcp/server.py` — MCP tools/resources and CLI transport setup.
- `examples/` — synthetic or explicitly redistributable fixtures only.
- `tests/` — behavior and regression tests.

Read `docs/architecture.md` before making parser/model changes.

## Required development loop

From a clean checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m build
```

On Windows, use the appropriate virtual-environment activation command instead of `source`.

Every behavior change should add or update tests. Parser bugs should be reduced to the smallest safe fixture that reproduces the issue.

## Electrical correctness invariants

1. **Never invent connectivity.** If the file does not provide enough information to resolve a connection, preserve an unknown state or emit a warning.
2. **Do not infer internal IC connectivity.** `trace_signal` follows resolved schematic nets only.
3. **Keep parser behavior deterministic.** The same file should produce the same canonical model without an LLM call.
4. **Preserve ambiguity.** Duplicate labels, ambiguous pin names, unsupported constructs, and unresolved hierarchy should be surfaced explicitly rather than silently normalized away.
5. **Prefer exact source evidence.** When adding future confidence-based adapters such as PDF parsing, attach confidence/source metadata rather than presenting uncertain results as exact net connectivity.

## Filesystem and execution safety

- Respect `SCHEMATIC_MCP_ROOT` and `--root` boundaries.
- Do not broaden file access without tests for `..`, absolute-path, and symlink escape cases.
- Do not execute arbitrary customer firmware, EDA scripts, macros, or project hooks merely to extract metadata.
- Prefer parsing explicit configuration over invoking compilers, preprocessors, or EDA executables.
- Keep network-facing transports loopback-only by default unless authentication and threat-model changes are deliberately designed and documented.

## Fixture privacy and licensing

Never commit proprietary customer schematics, Gerbers, BOMs, credentials, or confidential product information.

Fixtures must be one of:

- synthetic;
- created specifically for this repository;
- or accompanied by an explicit license/permission that allows public redistribution.

If provenance is uncertain, do not add the file.

## Adding a new EDA adapter

A new format adapter should:

1. parse its native format into the canonical model;
2. avoid adding vendor-specific branches to MCP query tools;
3. expose unsupported constructs through warnings/metadata;
4. include a minimal fixture corpus;
5. include tests for components, pins, nets, labels, and at least one format-specific edge case;
6. document supported versions and known limitations.

## Firmware validation changes

`validate_pinmap()` is intentionally framework-neutral. Framework-specific source extraction should produce an explicit pin contract first, then compare that contract against schematic nets.

Do not hide mismatches with fuzzy signal-name matching unless the API makes that normalization explicit and reports confidence.

## Pull requests

Before opening or updating a PR:

- run the full test suite;
- keep unrelated refactors out of the change;
- update README/docs for user-visible behavior;
- update `CHANGELOG.md` for notable user-facing additions/fixes;
- call out compatibility, security, and uncertainty risks in the PR body.

If a requested change conflicts with these invariants, explain the tradeoff in the PR rather than silently weakening them.
