"""Actual HTTP sockets, independent CLI process, and real MCP stdio transport."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from mcp import Client, StdioServerParameters

from test_vision import make_image, response


def test_http_api_to_cli_to_exports_and_offline_reload(tmp_path):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            assert self.path == "/v1/chat/completions"
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(data)
            if len(requests) == 1:
                body = response()
            else:
                body = response({"findings": [], "limitations": ["Synthetic response, not a real model evaluation"]})
            encoded = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        path = make_image(tmp_path / "drawing.png")
        output = tmp_path / "report"
        env = {**os.environ, "SCHEMATIC_LLM_MODEL": "synthetic-test", "SCHEMATIC_LLM_API_KEY": "fixture-key",
               "SCHEMATIC_LLM_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1"}
        result = subprocess.run([sys.executable, "-m", "schematic_mcp.cli", str(path), "--vision", "--llm-review", "--output", str(output)],
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert len(requests) == 2
        assert requests[0]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
        model = json.loads((output / "model.json").read_text())
        assert len(model["components"]) == 2
        report = json.loads((output / "review.json").read_text())
        assert report["coverage"]["llm_review"]
        assert report["findings"][0]["rule"] == "OUTPUT_CONFLICT"
        assert report["connectivity_status"] == "unverified"
        result = subprocess.run([sys.executable, "-m", "schematic_mcp.cli", str(output / "model.json"), "--output", str(tmp_path / "offline")],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert len(requests) == 2  # JSON reload never contacts a provider.
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_mcp_stdio_subprocess_opens_reviews_and_returns_resource():
    root = Path(__file__).parents[1] / "examples"
    async def exercise():
        transport = StdioServerParameters(command=sys.executable, args=["-m", "schematic_mcp", "--root", str(root)])
        async with Client(transport, raise_exceptions=True) as client:
            opened = await client.call_tool("open_schematic", {"path": "minimal.kicad_sch"})
            assert opened.structured_content["ok"]
            result = await client.call_tool("review_schematic", {})
            assert result.structured_content["review"]["connectivity_status"] == "source_resolved"
            resource = await client.read_resource("schematic://current/model")
            model = json.loads(resource.contents[0].text)
            assert len(model["components"]) == 2
            assert model["provenance"]["method"] == "native_parser"
            failed = await client.call_tool("open_schematic_model", {"path": "../secret.json"})
            assert failed.structured_content["ok"] is False
            trace = await client.call_tool("trace_signal", {"reference": "U1", "pin_number": "1"})
            assert trace.structured_content["endpoints"] == ["U2.1"]
    asyncio.run(exercise())
