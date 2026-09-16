# Open-source readiness and Codex for OSS notes

This document is a maintainer checklist for making `schematic-mcp` useful to the public first, and suitable for open-source program applications second.

Last reviewed: **2026-09-16**.

## Project value proposition

`schematic-mcp` turns hardware schematics into deterministic electrical context that MCP-compatible AI agents can query. The current public implementation focuses on modern KiCad `.kicad_sch` files and exposes components, pins, nets, signal tracing, MCU pin maps, and explicit firmware ↔ schematic pin-map validation without asking the agent to infer connectivity from screenshots.

The long-term direction is a vendor-neutral hardware context server spanning schematics, firmware pin definitions, BOM/PCB/manufacturing context, and multiple EDA ecosystems. See [`project-positioning.md`](project-positioning.md) for the full ecosystem thesis and project boundaries.

## Evidence we can claim today

Only claim facts that can be verified in the repository or public project history:

- public Apache-2.0 repository owned by `vonpanda` and not a fork;
- Python package metadata and CLI entry point at version `0.1.0`;
- 10 MCP tools plus structured resources backed by a canonical circuit model;
- modern KiCad parser;
- deterministic firmware ↔ schematic pin-map validation;
- synthetic public schematic and firmware fixtures with a reproducible mismatch demo;
- automated tests across Python 3.10/3.11/3.12 and package-build verification;
- MCP-client end-to-end test covering tool discovery and all exposed tools;
- filesystem-root restriction and security tests for safer agent use;
- explicit MCP tool behavior annotations;
- security policy, contribution guidance, code of conduct, issue/PR templates, changelog, public roadmap issues, and `AGENTS.md`;
- automated dependency maintenance;
- documented release workflow using PyPI Trusted Publishing (OIDC);
- MCP Registry metadata and ownership marker prepared for later official publication;
- third-party Glama MCP directory indexing that recognizes the server and its tool schema.

The Glama listing is evidence of external discoverability/indexing, **not evidence of end-user adoption**.

Do **not** invent GitHub stars, download counts, users, contributors, production deployments, package releases, or official registry publication.

## Current adoption and release snapshot

Checked on **2026-09-16**:

- GitHub stars: **0**;
- forks: **0**;
- GitHub Releases: **none published**;
- public PyPI downloads: **not available / not verified because no public package release is confirmed**;
- official MCP Registry publication: **not yet claimed**;
- third-party directory discoverability: **Glama indexes the server and 10-tool schema**.

The project is therefore best positioned today on **ecosystem importance + active maintenance**, not broad-adoption metrics.

## Evidence to accumulate

The strongest future application will add real third-party evidence:

- GitHub stars and forks;
- external issues and pull requests;
- package downloads after a public package release;
- independent users or downstream projects linking to `schematic-mcp`;
- compatibility fixtures contributed by hardware engineers;
- documented agent workflows where schematic context prevented a firmware/hardware integration mistake;
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
- [x] all 10 tools covered through the MCP client path
- [x] explicit tool behavior annotations
- [x] public roadmap issues with scoped acceptance criteria
- [x] coding-agent maintenance guide and dependency automation
- [x] explicit ecosystem positioning and project boundaries
- [x] tokenless PyPI release workflow prepared
- [x] MCP Registry metadata and publishing guide prepared
- [x] third-party MCP directory indexing observed
- [ ] publish tagged GitHub Release `v0.1.0`
- [ ] publish `schematic-mcp==0.1.0` to PyPI
- [ ] verify clean `pip`/`uvx` installation from PyPI
- [ ] publish to the official MCP Registry
- [ ] add at least one richer redistributable real-world/open-hardware fixture
- [ ] capture and publish a user-facing MCP client demo transcript/output

### 0.2 — meaningful hardware-agent workflow

- [ ] hierarchical KiCad project graph
- [ ] richer bus/net semantics
- [x] firmware ↔ schematic pin-map validation prototype
- [ ] framework-specific firmware pin extraction
- [ ] compatibility matrix across representative KiCad versions/exporters

## Release readiness

The first release path is already documented in [`releasing.md`](releasing.md). The repository currently aligns package/version metadata at `0.1.0` and has a release workflow that builds/tests artifacts and publishes to PyPI through Trusted Publishing only after a GitHub Release is published.

The remaining first-release steps require maintainer-authenticated setup/actions rather than repository code changes:

1. configure the PyPI pending Trusted Publisher and GitHub `pypi` environment;
2. run a release rehearsal;
3. publish GitHub Release `v0.1.0`;
4. verify the public package from a clean environment;
5. follow [`mcp-registry-publishing.md`](mcp-registry-publishing.md) for authenticated official Registry publication.

Do not weaken this process by adding a long-lived PyPI token merely to speed up publication.

## Current Codex for Open Source application checklist

Checked against the public OpenAI form on **2026-09-16**.

Current items relevant to this project:

- maintainers of active open-source projects may apply;
- GitHub profile and repository should be public;
- the form asks whether the applicant is a **primary** or **core** maintainer;
- the qualification answer may cite stars, monthly downloads, **or ecosystem importance**;
- OpenAI reviews usage, ecosystem importance, and evidence of active maintenance;
- the form includes interest in Codex Security and project API credits;
- API-credit applicants provide an OpenAI Organization ID and a short use statement;
- applications are reviewed on a rolling basis;
- projects that do not neatly fit usage/adoption criteria may still apply and explain why they matter to the ecosystem.

Current form: [Codex for Open Source](https://openai.com/form/codex-for-oss/).

The current final-copy draft is maintained in [`openai-codex-for-oss-application-draft.md`](openai-codex-for-oss-application-draft.md).

## Why the problem matters

Coding agents increasingly modify embedded firmware while critical hardware context remains locked inside EDA files. A wrong GPIO, I2C assumption, power-domain assumption, or signal mapping can create failures that source-code-only reasoning cannot detect. A structured schematic context layer makes those constraints available to agents through deterministic tools.

The public synthetic demo demonstrates this failure class: firmware swaps `SENSOR_INT` and `LED_STATUS` GPIO assignments while the schematic preserves the correct electrical mapping, and `validate_pinmap()` reports both mismatches explicitly. The repository's MCP-client end-to-end test exercises this through the actual protocol path rather than only internal Python helper calls.

## Credible API-credit use

If applying for API credits, describe work that benefits the public repository without turning the core parser into a hosted-model dependency. Good candidates include:

- public evals measuring whether coding agents detect firmware/hardware mismatches with and without schematic context;
- maintainer automation for issue triage and compatibility-fixture review;
- automated release-note and regression-review workflows;
- evaluation of framework-specific firmware extraction against deterministic schematic ground truth.

The core EDA parser and connectivity graph should remain deterministic and usable without an OpenAI API key.

## Application integrity rule

Always distinguish between:

- **implemented today**;
- **planned roadmap**;
- **measured adoption**;
- **external discoverability**;
- **hypothesized ecosystem value**.

Keeping these categories separate is more credible than overstating early traction.