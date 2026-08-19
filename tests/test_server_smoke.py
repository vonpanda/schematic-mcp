def test_mcp_server_imports_with_registered_tools():
    import schematic_mcp.server as server

    assert server.mcp is not None
    assert callable(server.validate_pinmap)
