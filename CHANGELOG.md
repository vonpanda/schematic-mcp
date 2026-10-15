# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows Semantic Versioning while practical during the pre-1.0 phase.

## [Unreleased]

### Added
- Explicit PDF/PNG/JPEG/WebP vision-LLM extraction with structured schema validation, page evidence, document fingerprint, scoped candidate nets and bounded rendering/API requests.
- Configurable Chat Completions-compatible endpoint/model, strict schema or explicit JSON mode, redacted provider failures and bounded retries.
- Local electrical review rules and separately requested LLM review hypotheses with validated endpoint citations and coverage limitations.
- Offline canonical JSON reload, graph consistency validation and the `schematic-review` CLI exporting JSON and Markdown reports.
- MCP extraction, JSON import and review tools; explicit remote-call annotations and unverified-data propagation.
- Synthetic HTTP/CLI/MCP stdio integration tests, PDF/image rendering and adversarial/failure/recovery regression coverage.

### Changed
- Canonical JSON now includes schema version, connectivity status, optional source evidence and provenance. Pin-map validation returns an additional `unverified` count and cannot pass for LLM/imported graphs.
- Workspace model/graph publication is atomic and failed extraction/import preserves the previous document.
- KiCad NC markers are retained on pins, including contradictory wired NC markers for review.

### Validation boundary
- No real-provider/model accuracy claim or production sign-off. Real API and human-labeled schematic acceptance remain required.

## [0.1.0] - 2026-08-19

### Added
- Initial MCP server for deterministic hardware schematic context.
- Modern KiCad `.kicad_sch` parser.
- Canonical component, pin, net, and circuit graph model.
- Component, pin, net, signal tracing, and MCU pin-map MCP tools.
- Firmware ↔ schematic pin-map validation by physical pin number or symbolic pin name.
- Synthetic ESP32-style firmware mismatch demo and regression tests.
- MCP-client end-to-end test covering tool discovery, schematic loading, and structured mismatch output.
- MCP resources for the current schematic summary and canonical model.
- Filesystem root restriction via `SCHEMATIC_MCP_ROOT` and `--root`, including path/symlink boundary tests.
- stdio and Streamable HTTP transports.
- Python 3.10/3.11/3.12 CI, dependency checks, and package-build verification.
- Security policy, code of conduct, contribution guidance, changelog, and contributor-facing issue/PR templates.
- Public roadmap issues, project positioning, OSS-readiness notes, and a truthful Codex for Open Source application draft.
- `AGENTS.md` with coding-agent architecture, safety, privacy, and electrical-correctness invariants.
- Dependabot configuration for Python and GitHub Actions dependencies.
- Official MCP Registry metadata preparation via `server.json`, README ownership marker, and metadata-alignment tests.
- Tokenless PyPI Trusted Publishing release workflow with separate build and OIDC publish jobs.
