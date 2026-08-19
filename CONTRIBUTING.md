# Contributing

Contributions are welcome, especially compatibility fixtures, parser improvements, hardware-agent workflows, tests, and documentation from real electronics projects.

## Development setup

```bash
git clone https://github.com/vonpanda/schematic-mcp.git
cd schematic-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

On Windows, activate the virtual environment with the appropriate PowerShell or Command Prompt script instead of `source`.

## Before opening a pull request

- keep changes focused and explain the hardware/agent problem being solved;
- add or update tests for behavior changes;
- use small synthetic or explicitly redistributable schematic fixtures;
- do not commit customer schematics, proprietary board data, credentials, or secrets;
- update user-facing documentation when tools, resources, CLI flags, or supported behavior change;
- run `pytest` locally.

## Parser design rule

For a new schematic format or EDA ecosystem, implement a separate adapter that produces the canonical model. Avoid adding format-specific behavior to the MCP tools themselves.

This separation keeps agent-facing queries stable while parsers evolve independently.

## Connectivity correctness

Electrical connectivity must be deterministic and conservative. If a parser cannot resolve a connection confidently, surface a warning or an explicit unknown state rather than inventing a connection.

Tests should state the expected electrical interpretation of each fixture, including edge cases such as junctions, labels, multi-unit symbols, hierarchical sheets, and buses.

## Bug reports

Please reduce parser bugs to the smallest schematic that still reproduces the problem. Synthetic fixtures are strongly preferred because they can become regression tests safely.

Security vulnerabilities should follow [SECURITY.md](SECURITY.md) instead of being reported publicly.

## Licensing

By contributing, you agree that your contribution is licensed under the Apache License 2.0 used by this repository.
