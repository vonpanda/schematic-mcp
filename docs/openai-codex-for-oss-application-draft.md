# OpenAI Codex for Open Source — application draft

> Maintainer working draft. Re-check the public OpenAI form and all live adoption metrics immediately before submitting. Do not copy stale stars, forks, downloads, or program terms into an application.

Form checked: **2026-08-19**

Repository: `https://github.com/vonpanda/schematic-mcp`

## Identity fields

- First name: **fill from the ChatGPT account holder's legal/preferred application details**
- Last name: **fill from the ChatGPT account holder's legal/preferred application details**
- Email: **use the email associated with the ChatGPT account**
- GitHub username: `vonpanda`
- GitHub repository URL: `https://github.com/vonpanda/schematic-mcp`
- Role: **Primary maintainer**

Before submission, confirm that both the GitHub profile and repository are public as required by the form.

## Why does this repository qualify?

Current form limit: **500 characters**.

Recommended truthful answer (**414 characters** at time of drafting):

> `schematic-mcp` is a new Apache-2.0 hardware-context MCP server for AI coding agents. It deterministically parses KiCad schematics into a canonical electrical graph and validates firmware pin assumptions against real nets. CI tests the MCP client flow on Python 3.10–3.12. The repository is early (0 stars/0 forks today), so I am applying based on ecosystem importance and active maintenance, not claimed adoption.

### Refresh before submitting

Replace `0 stars/0 forks today` with a fresh dated metric if the public counts have changed. If a package release exists by then, add only a verified download metric that fits within the 500-character limit.

## Interests

Suggested selection:

- **API credits for my project** — yes, if the maintainer has an OpenAI Organization ID and intends to run the public eval/maintenance work below.
- **Codex Security** — optional. Select it only if the maintainer genuinely wants the project evaluated for conditional access; do not imply that access is required for the project to function.

## OpenAI Organization ID

- **Fill immediately before submission from the maintainer's OpenAI organization.**
- Never commit API keys, organization secrets, or private account credentials to this repository.

## How will you use API credits for your project?

Current form limit: **500 characters**.

Recommended answer (**282 characters** at time of drafting):

> API credits would fund open-source evals comparing coding agents with and without schematic context, maintainer automation for compatibility fixtures/issues, and regression/release review workflows. The core EDA parser will remain deterministic and usable without an OpenAI API key.

## Anything else we should know?

Current form limit: **500 characters**.

Recommended answer (**292 characters** at time of drafting):

> The project was created to make hardware design truth a first-class input to coding agents, rather than another KiCad GUI automation layer. It is file-driven, headless-friendly, and designed around vendor-neutral adapters so future Altium/EasyEDA/PDF sources can expose the same MCP contract.

## Evidence supporting the application

At the time this draft was prepared, the repository already includes:

- an Apache-2.0 public codebase;
- a deterministic modern KiCad `.kicad_sch` parser;
- a canonical component/pin/net graph;
- MCP tools/resources for schematic inspection and signal tracing;
- `validate_pinmap()` for firmware ↔ schematic verification;
- a synthetic firmware bug demo with two intentional GPIO mismatches;
- an MCP-client end-to-end CI test that opens the schematic and verifies structured mismatch output;
- CI on Python 3.10/3.11/3.12 plus package-build verification;
- filesystem boundary/security tests;
- security, contribution, code-of-conduct, changelog, issue/PR templates, public roadmap issues, `AGENTS.md`, and Dependabot configuration;
- explicit project positioning around deterministic, file-driven, vendor-neutral hardware context.

These are **maintenance and technical-capability signals**, not evidence of broad adoption.

## Current adoption snapshot

Initial public snapshot recorded on 2026-08-19:

- stars: **0**;
- forks: **0**;
- PyPI/package downloads: **not available yet**;
- first tagged public release: **not published yet**.

Refresh all values before submission.

## Submission strategy

The form explicitly allows projects that do not neatly fit usage/adoption criteria to explain why they matter to the ecosystem. For the current early-stage repository, the application should therefore emphasize:

1. the embedded-coding-agent problem that source-code-only reasoning cannot solve;
2. deterministic EDA parsing rather than LLM-guessed connectivity;
3. vendor-neutral hardware context as reusable infrastructure;
4. firmware ↔ schematic validation as a concrete working example;
5. active maintenance evidence from tests, CI, PRs, issues, security and release preparation;
6. measured adoption only when real public adoption exists.

Do not claim broad adoption until third-party evidence exists.

## Remaining improvements before the strongest submission

- publish a tagged release;
- publish an installable package if the distribution name is available;
- set useful GitHub repository topics;
- obtain genuine third-party usage, stars, issues, pull requests, or fixture contributions;
- capture a public MCP-client demo transcript/output;
- add a richer redistributable compatibility fixture or real open-hardware example.

Applying before those items is still possible under the ecosystem-importance path, but the application becomes stronger as real adoption and release evidence accumulate.
