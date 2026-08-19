# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows Semantic Versioning while practical during the pre-1.0 phase.

## [Unreleased]

### Added
- Open-source project governance and security documentation.
- Additional workspace and graph behavior tests.
- Contributor-facing issue and pull request templates.
- OSS readiness notes for maintainers.
- Firmware ↔ schematic pin-map validation by physical pin number or symbolic pin name.
- Synthetic ESP32-style firmware mismatch demo and regression tests.

## [0.1.0] - 2026-08-19

### Added
- Initial MCP server for hardware schematic context.
- Modern KiCad `.kicad_sch` parser.
- Canonical component, pin, net, and circuit graph model.
- Component, pin, net, signal tracing, and MCU pin-map MCP tools.
- MCP resources for the current schematic summary and canonical model.
- Filesystem root restriction via `SCHEMATIC_MCP_ROOT` and `--root`.
- stdio and Streamable HTTP transports.
- Initial parser and multi-unit symbol tests.
