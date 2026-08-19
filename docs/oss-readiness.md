# Open-source readiness and Codex for OSS notes

This document is a maintainer checklist for making `schematic-mcp` useful to the public first, and suitable for open-source program applications second.

## Project value proposition

`schematic-mcp` turns hardware schematics into deterministic electrical context that MCP-compatible AI agents can query. The initial implementation focuses on modern KiCad `.kicad_sch` files and exposes components, pins, nets, signal tracing, MCU pin maps, and explicit firmware ↔ schematic pin-map validation without requiring an agent to infer connectivity from screenshots.

The long-term direction is a vendor-neutral hardware context server spanning schematics, firmware pin definitions, BOM/PCB/manufacturing context, and multiple EDA ecosystems. See [`project-positioning.md`](project-positioning.md) for the full ecosystem thesis and project boundaries.

## Evidence we can claim today

Only claim facts that can be verified in the repository or public project history:

- public Apache-2.0 repository;
- working Python package and CLI entry point;
- MCP tools/resources backed by a canonical circuit model;
- modern KiCad parser;
- automated tests across Python 3.10/3.11/3.12 and package-build verification;
- MCP-client end-to-end test covering tool discovery, schematic loading, and structured firmware-validation output;
- synthetic public schematic and firmware fixtures;
- deterministic firmware ↔ schematic pin-map validation with a reproducible mismatch demo;
- filesystem-root restriction for safer agent use;
- security policy, contribution guidance, issue/PR templates, and public roadmap issues;
- coding-agent maintenance rules in `AGENTS.md`;
- automated dependency-maintenance configuration;
- documented roadmap, architecture, and project positioning.

Do **not** invent GitHub stars, download counts, users, contributors, production deployments, or external adoption.

### Adoption baseline

A first public baseline was recorded on **2026-08-19**, shortly after repository creation:

- GitHub stars: **0**;
- forks: **0**;
- package-registry downloads: **not available yet** because no public package release has been published.

This is a dated baseline, not a live metric. Future applications should use fresh public counts and keep the measurement date.

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
- [x] synthetic schematic fixture
- [x] synthetic firmware ↔ schematic mismatch demo
- [x] MCP-client end-to-end CI test
- [x] public roadmap issues with scoped acceptance criteria
- [x] coding-agent maintenance guide and dependency automation
- [x] explicit ecosystem positioning and project boundaries
- [ ] publish a tagged GitHub release
- [ ] publish package to PyPI, if the package name is available
- [ ] add at least one richer, redistributable real-world fixture
- [ ] capture and publish a user-facing MCP client demo transcript/output

### 0.2 — meaningful hardware-agent workflow

- [ ] hierarchical KiCad project graph
- [ ] richer bus/net semantics
- [x] firmware ↔ schematic pin-map validation prototype
- [ ] framework-specific firmware pin extraction
- [ ] compatibility matrix across representative KiCad versions/exporters

### Adoption milestone

Before submitting an application that emphasizes usage, prefer real evidence such as external stars, issues, contributors, downstream references, or package downloads. If usage is still small, lead with technical/ecosystem importance and clearly label the project as early-stage.

## Current Codex for Open Source application checklist

Checked against the public OpenAI form on **2026-08-19**. Re-check the form before submitting because program terms and fields may change.

Current form/criteria items relevant to this project include:

- applicant is the **primary or core maintainer** of an active public open-source repository;
- GitHub profile and repository should be public;
- the application asks why the repository qualifies, with examples such as GitHub stars, monthly downloads, or ecosystem importance;
- OpenAI states that it reviews signals including meaningful usage, broad adoption, clear ecosystem importance, and evidence of active maintenance;
- the form includes optional interest in Codex Security and API credits;
- API-credit applicants provide an OpenAI Organization ID and a short explanation of how credits will support the project;
- applications are reviewed on a rolling basis;
- projects that do not neatly fit usage/adoption criteria may still explain why they matter to the ecosystem.

Current form: [Codex for Open Source](https://openai.com/form/codex-for-oss/).

## Draft application positioning

A concise, truthful positioning statement:

> `schematic-mcp` is an open-source hardware-context MCP server for AI coding agents. It deterministically parses EDA source files into a canonical electrical graph and exposes queryable components, pins, nets, signal traces, and firmware ↔ schematic pin validation. The project starts with KiCad but is intentionally designed around vendor-neutral adapters so embedded coding agents can verify hardware assumptions instead of reasoning from source code or screenshots alone.

## Why the problem matters

Coding agents increasingly modify embedded firmware while critical hardware context remains locked inside EDA files. A wrong GPIO, I2C assumption, power-domain assumption, or signal mapping can create failures that source-code-only reasoning cannot detect. A structured schematic context layer makes those constraints available to agents through deterministic tools.

The public synthetic demo already demonstrates this class of failure: firmware swaps `SENSOR_INT` and `LED_STATUS` GPIO assignments while the schematic preserves the correct electrical mapping, and `validate_pinmap()` reports both mismatches explicitly. The repository's MCP-client end-to-end test verifies this flow through the actual SDK client/tool protocol path rather than only through internal Python helper calls.

## Credible API-credit use

If applying for API credits, describe work that genuinely benefits the public repository rather than adding an API dependency to core parsing.

Good candidates include:

- open-source evals measuring whether coding agents detect firmware/hardware mismatches with and without schematic context;
- maintainer automation for issue triage and compatibility-fixture review;
- automated release-note and regression-review workflows;
- evaluation of framework-specific firmware extraction against the deterministic schematic ground truth.

The core EDA parser and connectivity graph should remain deterministic and usable without an OpenAI API key.

## Application integrity rule

Application text must distinguish between:

- **implemented today**;
- **planned roadmap**;
- **measured adoption**;
- **hypothesized ecosystem value**.

Keeping these categories separate makes the project more credible than overstating early traction.
