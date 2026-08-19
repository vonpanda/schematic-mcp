import asyncio
from pathlib import Path

from mcp import Client

import schematic_mcp.server as server
from schematic_mcp.workspace import Workspace

EXAMPLES = Path(__file__).parents[1] / "examples"


async def _exercise_mcp_protocol() -> None:
    previous_workspace = server.workspace
    isolated_workspace = Workspace()
    isolated_workspace.root = EXAMPLES.resolve()
    server.workspace = isolated_workspace

    try:
        async with Client(server.mcp, raise_exceptions=True) as client:
            tools = await client.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            assert "open_schematic" in tool_names
            assert "validate_pinmap" in tool_names

            opened = await client.call_tool(
                "open_schematic",
                {"path": "esp32_firmware_validation.kicad_sch"},
            )
            assert opened.is_error is False
            assert opened.structured_content is not None
            assert opened.structured_content["ok"] is True
            assert opened.structured_content["summary"]["components"] == 3

            validation = await client.call_tool(
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
            assert validation.is_error is False
            assert validation.structured_content is not None
            assert validation.structured_content["ok"] is False
            assert validation.structured_content["summary"]["matched"] == 2
            assert validation.structured_content["summary"]["mismatched"] == 2
    finally:
        server.workspace = previous_workspace


def test_mcp_client_can_open_and_validate_schematic_end_to_end():
    asyncio.run(_exercise_mcp_protocol())
