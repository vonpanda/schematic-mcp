# Contributing

Contributions are welcome.

## Development

```bash
git clone https://github.com/vonpanda/schematic-mcp.git
cd schematic-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Please add or update tests for parser and connectivity changes. For new schematic formats, implement a separate adapter that outputs the canonical model instead of adding format-specific behavior to the MCP tools.

By contributing, you agree that your contribution is licensed under Apache License 2.0.
