# Open-source readiness and Codex for OSS notes

This document is a maintainer checklist for making `schematic-mcp` useful to the public first, and suitable for open-source program applications second.

## Project value proposition

`schematic-mcp` turns hardware schematics into deterministic electrical context that MCP-compatible AI agents can query. The initial implementation focuses on modern KiCad `.kicad_sch` files and exposes components, pins, nets, signal tracing, and MCU pin maps without requiring an agent to infer connectivity from screenshots.

The long-term direction is a vendor-neutral hardware context server spanning schematics, firmware pin definitions, BOM/PCB/manufacturing context, and multiple EDA ecosystems.

## Evidence we can claim today

Only claim facts that can be verified in the repository or public project history:

- public Apache-2.0 repository;
- working Python package and CLI entry point;
- MCP tools/resources backed by a canonical circuit model;
- modern KiCad parser;
- automated tests and CI;
- synthetic public example fixture;
- filesystem-root restriction for safer agent use;
- documented roadmap and architecture.

Do **not** invent GitHub stars, download counts, users, contributors, production deployments, or external adoption.

## Evidence to accumulate before applying

The strongest application will have real third-party evidence. Track these over time:

- GitHub stars and forks;
- external issues and pull requests;
- package downloads after a public package release;
- independent users or projects linking to `schematic-mcp`;
- compatibility fixtures contributed by hardware engineers;
- documented examples of an AI agent using schematic context to prevent a firmware/hardware integration mistake;
- release history and maintenance cadence.

## Near-term milestones

### 0.1.x — credible public alpha

- [x] public repository and OSI-approved license
- [x] installable package metadata
- [x] MCP server and core tools
- [x] KiCad parser and circuit graph
- [x] initial tests and CI
- [x] security policy and contribution guidance
- [x] issue / pull request templates
- [x] synthetic demo fixture
- [ ] publish a tagged GitHub release
- [ ] publish package to PyPI, if the package name is available
- [ ] add at least one richer, redistributable real-world fixture
- [ ] document an end-to-end agent demo with captured tool output

### 0.2 — meaningful hardware-agent workflow

- [ ] hierarchical KiCad project graph
- [ ] richer bus/net semantics
- [ ] firmware ↔ schematic pin-map validation prototype
- [ ] compatibility matrix across representative KiCad versions/exporters

### Adoption milestone

Before submitting an application that emphasizes usage, prefer real evidence such as external stars, issues, contributors, downstream references, or package downloads. If usage is still small, lead with technical/ecosystem importance and clearly label the project as early-stage.

## Draft application positioning

A concise, truthful positioning statement:

> `schematic-mcp` is an open-source MCP server that gives AI coding agents deterministic access to hardware schematic connectivity. Instead of asking a model to infer nets and pin mappings from an image, it parses EDA source files into a canonical graph and exposes queryable components, pins, nets, signal traces, and MCU pin maps. The project starts with KiCad and aims to become a vendor-neutral hardware context layer for firmware and electronics workflows.

## Why the problem matters

Coding agents increasingly modify embedded firmware while critical hardware context remains locked inside EDA files. A wrong GPIO, I2C address assumption, power-domain assumption, or signal mapping can create failures that source-code-only reasoning cannot detect. A structured schematic context layer makes those constraints available to agents through deterministic tools.

## Application integrity rule

Application text must distinguish between:

- **implemented today**;
- **planned roadmap**;
- **measured adoption**;
- **hypothesized ecosystem value**.

Keeping these categories separate makes the project more credible than overstating early traction.
