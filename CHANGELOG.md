# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows Semantic Versioning while practical during the pre-1.0 phase.

## [Unreleased]

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
