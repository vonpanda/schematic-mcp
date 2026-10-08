import asyncio
from pathlib import Path

from mcp import Client

import schematic_mcp.server as server
from schematic_mcp.workspace import Workspace

EXAMPLES = Path(__file__).parents[1] / "examples"


async def _call_ok(client: Client, name: str, arguments: dict | None = None):
    result = await client.call_tool(name, arguments or {})
    assert result.is_error is False
    assert result.structured_content is not None
    return result.structured_content


async def _exercise_mcp_protocol() -> None:
    previous_workspace = server.workspace
    isolated_workspace = Workspace()
    isolated_workspace.root = EXAMPLES.resolve()
    server.workspace = isolated_workspace

    try:
        async with Client(server.mcp, raise_exceptions=True) as client:
            listed = await client.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            expected_names = {
                "open_schematic",
                "open_schematic_project",
                "open_schematic_model",
                "extract_schematic",
                "review_schematic",
                "review_schematic_with_llm",
                "schematic_summary",
                "list_components",
                "get_component",
                "get_pin",
                "list_nets",
                "get_net",
                "trace_signal",
                "get_mcu_pinmap",
                "validate_pinmap",
            }
            assert set(tools) == expected_names

            for name, tool in tools.items():
                assert tool.annotations is not None
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.idempotent_hint is (name not in {"extract_schematic", "review_schematic_with_llm"})
                assert tool.annotations.open_world_hint is (name in {"extract_schematic", "review_schematic_with_llm"})
                assert tool.annotations.read_only_hint is (name not in {"open_schematic", "open_schematic_project", "open_schematic_model", "extract_schematic"})

            opened = await _call_ok(
                client,
                "open_schematic",
                {"path": "esp32_firmware_validation.kicad_sch"},
            )
            assert opened["ok"] is True
            assert opened["summary"]["components"] == 3

            summary = await _call_ok(client, "schematic_summary")
            assert summary["ok"] is True
            assert summary["components"] == 3

            components = await _call_ok(client, "list_components")
            assert components["ok"] is True
            assert components["count"] == 3

            component = await _call_ok(client, "get_component", {"reference": "U1"})
            assert component["ok"] is True
            assert component["component"]["reference"] == "U1"

            pin = await _call_ok(client, "get_pin", {"reference": "U1", "pin_number": "1"})
            assert pin["ok"] is True
            assert pin["pin"]["net"] == "I2C_SDA"

            nets = await _call_ok(client, "list_nets")
            assert nets["ok"] is True
            assert nets["count"] >= 1

            net = await _call_ok(client, "get_net", {"name": "I2C_SDA"})
            assert net["ok"] is True
            assert net["net"]["name"] == "I2C_SDA"

            trace = await _call_ok(client, "trace_signal", {"reference": "U1", "pin_number": "1"})
            assert trace["ok"] is True
            assert trace["net"] == "I2C_SDA"

            pinmap = await _call_ok(client, "get_mcu_pinmap", {"reference": "U1"})
            assert pinmap["ok"] is True
            assert pinmap["reference"] == "U1"

            validation = await _call_ok(
                client,
                "validate_pinmap",
                {
                    "reference": "U1",
                    "expected": {
                        "GPIO8": "I2C_SDA",
                        "GPIO9": "I2C_SCL",
                        "GPIO12": "LED_STATUS",
                        "GPIO13": "SENSOR_INT",
                    },
                },
            )
            assert validation["ok"] is False
            assert validation["summary"]["matched"] == 2
            assert validation["summary"]["mismatched"] == 2
    finally:
        server.workspace = previous_workspace


def test_mcp_client_exercises_all_tools_end_to_end():
    asyncio.run(_exercise_mcp_protocol())
