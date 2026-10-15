# OpenAI Codex for Open Source — application draft

> Maintainer working draft. Re-check the public OpenAI form and all live adoption metrics immediately before submitting. Do not claim users, downloads, releases, or registry publication that cannot be independently verified.

Form checked: **2026-09-16**

Repository: `https://github.com/vonpanda/schematic-mcp`

## Identity fields

- First name: **fill from the ChatGPT account holder's legal/preferred application details**
- Last name: **fill from the ChatGPT account holder's legal/preferred application details**
- Email: **use the email associated with the ChatGPT account**
- GitHub username: `vonpanda`
- GitHub repository URL: `https://github.com/vonpanda/schematic-mcp`
- Role: **Primary maintainer**

The public OpenAI form currently asks for a public GitHub profile and public repository, the maintainer role, one 500-character qualification statement, interest in Codex Security/API credits, an OpenAI Organization ID, a 500-character API-credit use statement, and an optional 500-character additional note.

## Final application copy

### Why does this repository qualify?

Current form limit: **500 characters**.

Recommended answer (**406 characters**):

> schematic-mcp is an Apache-2.0 hardware-context MCP server for AI coding agents. It deterministically parses KiCad schematics into a canonical electrical graph and validates firmware pin assumptions against real nets, solving failures source-code-only agents cannot reliably detect. The project has active CI, tests, security/contribution workflows, and is independently indexed in the Glama MCP directory.

### Interests

Suggested selection:

- **API credits for my project** — yes, if the maintainer has an OpenAI Organization ID and intends to run the public eval/maintenance work below.
- **Codex Security** — reasonable to select if the maintainer wants the repository considered for conditional security coverage; do not imply that access is required for the project to function.

### OpenAI Organization ID

- **Fill immediately before submission from the maintainer's OpenAI organization.**
- Never commit API keys, organization secrets, or private account credentials to this repository.

### How will you use API credits for your project?

Current form limit: **500 characters**.

Recommended answer (**279 characters**):

> API credits would fund public evals comparing coding agents with and without schematic context, maintainer automation for issue/fixture triage, and regression/release review workflows. The deterministic parser and circuit graph will remain fully usable without an OpenAI API key.

### Anything else we should know?

Current form limit: **500 characters**.

Recommended answer (**352 characters**):

> This is an early-stage project, so I am not claiming broad adoption. Its goal is to make hardware design truth a first-class input to coding agents through a file-driven, headless, vendor-neutral MCP layer. KiCad is implemented first; future adapters can expose Altium, EasyEDA, PDF/image, PCB, BOM, and manufacturing context through the same contract.

## Evidence supporting the application

Verified from the public repository as of 2026-09-16:

- public Apache-2.0 repository owned by `vonpanda` and not a fork;
- package/CLI version metadata aligned at `0.1.0`;
- deterministic modern KiCad `.kicad_sch` parser;
- canonical component/pin/net graph;
- 10 MCP tools plus structured MCP resources;
- `validate_pinmap()` for firmware ↔ schematic verification;
- synthetic public firmware/schematic mismatch demo;
- MCP-client end-to-end CI coverage, including tool enumeration and execution;
- CI across Python 3.10/3.11/3.12 plus package-build verification;
- filesystem-boundary/security tests;
- `SECURITY.md`, `CONTRIBUTING.md`, code of conduct, changelog, issue/PR templates, `AGENTS.md`, Dependabot, release workflow, and release/registry documentation;
- MCP Registry metadata (`server.json`) and README ownership marker prepared for future official publication;
- third-party Glama MCP directory indexing that recognizes the server and its 10 tools.

The Glama listing is evidence of external discoverability/indexing, **not evidence of end-user adoption**.

## Current adoption/release snapshot

Checked on **2026-09-16**:

- GitHub stars: **0**;
- forks: **0**;
- GitHub Releases: **none published**;
- public PyPI release/download count: **not verified / not available yet**;
- official MCP Registry publication: **not yet claimed**;
- third-party directory discoverability: **Glama indexes the server and tool schema**.

Do not replace these with stronger claims until the relevant public evidence exists.

## Why the ecosystem-importance path is credible

The application should lead with ecosystem value rather than usage volume. Embedded coding agents routinely need hardware facts that are not present in source code: physical MCU pin mapping, named nets, component connectivity, and schematic-vs-firmware consistency. `schematic-mcp` exposes those facts as deterministic structured context rather than asking a model to infer electrical connectivity from screenshots or prose.

This aligns with the OpenAI form's explicit statement that projects which do not neatly fit usage/adoption criteria may still apply if they play an important role in the ecosystem.

## Release and registry readiness

The repository is technically prepared for a first `v0.1.0` release:

- `pyproject.toml`, package `__version__`, and `server.json` use `0.1.0`;
- `.github/workflows/release.yml` builds/tests artifacts and uses PyPI Trusted Publishing (OIDC) on a published GitHub Release;
- `docs/releasing.md` documents the pending Trusted Publisher setup and first-release procedure;
- `docs/mcp-registry-publishing.md` correctly gates official Registry publication on a matching public PyPI package and tagged release.

What still requires authenticated maintainer action outside this repository-editing session:

1. configure the PyPI pending Trusted Publisher / GitHub `pypi` environment;
2. run a release rehearsal;
3. publish GitHub Release `v0.1.0`;
4. verify the package on PyPI from a clean environment;
5. publish to the official MCP Registry using the maintainer-authenticated publisher flow.

## Remaining improvements that would materially strengthen a later application

- publish the first tagged release and PyPI distribution;
- publish to the official MCP Registry;
- obtain genuine third-party usage evidence: stars, issues, pull requests, downstream references, package downloads, or compatibility fixtures;
- publish a user-facing MCP client demo transcript/output;
- add a richer redistributable real-world/open-hardware fixture.

Applying now is truthful under the ecosystem-importance path; applying after the release/registry steps would add stronger release-management and discoverability evidence.