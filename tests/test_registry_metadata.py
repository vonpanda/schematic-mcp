import json
from pathlib import Path

import schematic_mcp

ROOT = Path(__file__).parents[1]


def test_mcp_registry_metadata_matches_python_package():
    metadata = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))

    assert metadata["name"] == "io.github.vonpanda/schematic-mcp"
    assert metadata["version"] == schematic_mcp.__version__
    assert metadata["repository"] == {
        "url": "https://github.com/vonpanda/schematic-mcp",
        "source": "github",
    }

    assert len(metadata["packages"]) == 1
    package = metadata["packages"][0]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == "schematic-mcp"
    assert package["version"] == schematic_mcp.__version__
    assert package["transport"]["type"] == "stdio"
    assert package["runtimeHint"] == "uvx"


def test_readme_contains_registry_ownership_marker():
    metadata = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert f"<!-- mcp-name: {metadata['name']} -->" in readme
