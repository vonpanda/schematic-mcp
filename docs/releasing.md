# Releasing

The release process is designed around **PyPI Trusted Publishing (OIDC)** so the repository does not need a long-lived PyPI API token.

Workflow: `.github/workflows/release.yml`

## Safety model

The workflow separates building from publishing:

- the `build` job has normal read-only repository permissions, runs tests, builds the wheel/sdist, validates package metadata, and uploads artifacts;
- the `pypi-publish` job runs only for a published GitHub Release, downloads already-built artifacts, and receives only the OIDC permission needed for Trusted Publishing;
- no PyPI username, password, or API token is stored in the repository;
- a manual `workflow_dispatch` run performs a release rehearsal but **does not publish to PyPI**.

## One-time PyPI setup for the first release

PyPI supports **pending Trusted Publishers**, which can create the project on first successful OIDC publish. This avoids a manual token-based first upload.

In the PyPI account's Publishing page, configure a pending GitHub Actions publisher with these values:

- PyPI project name: `schematic-mcp`
- GitHub owner: `vonpanda`
- GitHub repository: `schematic-mcp`
- workflow filename: `release.yml`
- GitHub environment: `pypi`

A pending publisher does **not** reserve the project name until the first package is actually uploaded. Re-check that the distribution name is still available immediately before publishing.

The GitHub `pypi` environment is strongly recommended because it can be configured with release restrictions or maintainer approval.

## Release rehearsal

Before publishing a real GitHub Release, run the **Release** workflow manually from GitHub Actions.

A manual run executes only the build job and verifies:

1. the test suite passes;
2. sdist and wheel can be built;
3. `twine check` accepts package metadata;
4. release artifacts are produced.

It intentionally skips the PyPI publishing job.

## First public release

The repository currently uses package version `0.1.0`. Because no public package release existed while the repository was being prepared, all work intended for the first public alpha should be represented consistently as `0.1.0` before publishing.

Before creating the GitHub Release, verify:

- `pyproject.toml` version;
- `src/schematic_mcp/__init__.py` version;
- `server.json` version and PyPI package version;
- `CHANGELOG.md` release entry;
- all CI checks on `main`;
- the PyPI pending Trusted Publisher configuration above.

Create the GitHub Release using tag:

```text
v0.1.0
```

The release workflow explicitly fails if the GitHub Release tag does not equal `v` + the Python package version.

Publishing the GitHub Release triggers the tokenless PyPI job. If the pending publisher was configured correctly, PyPI creates the project during the first successful upload and converts the pending publisher into a normal trusted publisher.

## After PyPI succeeds

Verify from a clean environment:

```bash
python -m pip install schematic-mcp
schematic-mcp --help
```

If `uv` is available, also verify the intended isolated execution path:

```bash
uvx schematic-mcp --help
```

Then follow [`mcp-registry-publishing.md`](mcp-registry-publishing.md) to publish `server.json` to the official MCP Registry.

## Failed release behavior

Do not weaken the workflow by adding long-lived package tokens merely to bypass an OIDC configuration failure.

If publishing fails:

1. inspect the GitHub Actions log;
2. confirm the PyPI pending/normal publisher has the exact owner, repository, workflow filename, environment, and project name;
3. confirm the release tag matches the package version;
4. fix configuration or metadata;
5. publish a corrected release/version when necessary rather than silently overwriting artifacts.

PyPI distributions are immutable once uploaded, so treat the release version as final after a successful publish.
