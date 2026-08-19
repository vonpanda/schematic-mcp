# MCP Registry publishing

`schematic-mcp` includes `server.json` and the README ownership marker required to prepare for publication in the official MCP Registry.

**The server is not considered published to the MCP Registry merely because these files exist.**

## Planned registry identity

- MCP server name: `io.github.vonpanda/schematic-mcp`
- package registry: PyPI
- planned Python distribution: `schematic-mcp`
- transport: stdio
- metadata source: `server.json`

The official MCP Registry is currently a discovery/metadata registry. The Python package itself must be hosted on a supported public package registry such as PyPI.

## Publication gate

Do not run the final registry publish step until all of the following are true:

1. a matching tagged project release exists;
2. the exact Python distribution/version referenced by `server.json` exists publicly on PyPI;
3. the PyPI project description contains the README ownership marker:
   `mcp-name: io.github.vonpanda/schematic-mcp`;
4. the package installs in a clean environment and starts the `schematic-mcp` entry point;
5. `server.json`, `src/schematic_mcp/__init__.py`, `pyproject.toml`, and the release tag all use the same version;
6. normal CI is green;
7. the maintainer has reviewed the current MCP Registry schema and publishing documentation for changes.

## Why the README marker exists

For PyPI-backed MCP servers, the official Registry verifies package ownership by looking for a matching `mcp-name:` value in the package README/description.

The marker is intentionally placed in an HTML comment near the top of the root README so it is included in the PyPI long description without adding visual noise.

## Publish flow after the gate is satisfied

Use the current official MCP Registry publisher documentation rather than copying old commands from third-party tutorials.

The current documented GitHub-authenticated flow includes:

```bash
mcp-publisher login github
mcp-publisher publish
```

Then verify the published metadata through the official Registry API/search.

Publishing requires maintainer authentication and is therefore intentionally not automated from an unauthenticated repository setup session.

## Version updates

Every package release that will be advertised through the MCP Registry should update all version-bearing metadata together.

The repository test `tests/test_registry_metadata.py` currently guards alignment between:

- `server.json` version;
- Python package `__version__`;
- PyPI package identifier;
- MCP namespace ownership marker.

Release tooling should extend this check rather than duplicating independent version strings.

## Current limitation

The repository metadata is **prepared**, but the first PyPI package and official MCP Registry publication still require maintainer-side authenticated release actions.
