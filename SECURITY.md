# Security Policy

## Supported versions

`schematic-mcp` is currently pre-1.0 software. Security fixes are applied to the latest released minor version and the `main` branch.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a security vulnerability.

Use GitHub's private security advisory flow for this repository when available. If that is unavailable, contact the maintainer through the contact method listed on the maintainer's GitHub profile and clearly mark the report as a security issue.

Please include:

- affected version or commit;
- a minimal reproduction;
- expected and actual behavior;
- security impact;
- suggested mitigation, if known.

We aim to acknowledge valid reports promptly and coordinate a fix before public disclosure.

## Security model

`schematic-mcp` can read local schematic files. When it is used by an AI agent, configure `SCHEMATIC_MCP_ROOT` or `--root` so the server can only open files inside an intended hardware project directory.

The Streamable HTTP transport is intended for trusted development environments unless authentication and network controls are added by the operator. Do not expose an unauthenticated instance directly to the public internet.

## Optional LLM data transmission

Native parsing, queries, canonical JSON import and local review are offline. Explicit `extract_schematic` / CLI `--vision` sends rendered drawing images to the configured provider. `review_schematic_with_llm` / `--llm-review` sends structured circuit and source metadata. These calls may incur charges; configure credentials in the server environment and verify provider data policies before using confidential drawings. Do not place credentials in a URL or commit them to the repository.

HTTP is allowed only for loopback inference; remote endpoints require HTTPS and redirects are disabled. Provider response bodies are not included in user-facing errors. Input, page, pixel, output and retry bounds are documented in `docs/vision-and-review.md`. Drawing text and model output are untrusted: structured and graph validation cannot establish the truth of model-extracted connectivity or reasoning. Imported JSON never gains native-parser trust.

One server process contains one shared workspace, with no per-user isolation or HTTP authentication. Use separate local processes for separate users/projects. Do not expose the current HTTP server to an untrusted network.
