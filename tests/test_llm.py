import json

import httpx
import pytest

from schematic_mcp.llm import JSONClient, LLMConfig, LLMError
from schematic_mcp.parsers.vision_schema import PageExtraction
from test_vision import extraction, response


@pytest.mark.parametrize("url", ["http://example.com/v1", "file:///tmp/api", "https://user:secret@example.com/v1", "https://example.com/v1?key=secret", "https://example.com/v1#fragment"])
def test_unsafe_configuration_rejected(url):
    with pytest.raises(ValueError):
        LLMConfig(model="model", api_key="secret", base_url=url)


@pytest.mark.parametrize("options", [{"model": ""}, {"api_key": ""}, {"timeout": float("nan")}, {"timeout": 0}, {"retries": 4}, {"max_tokens": 0}, {"response_format": "text"}])
def test_configuration_validation(options):
    with pytest.raises(ValueError):
        LLMConfig(**({"model": "model", "api_key": "secret"} | options))


@pytest.mark.parametrize("mode", ["json_schema", "json_object"])
def test_request_uses_actual_image_and_schema_and_hides_key(mode):
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        assert body["response_format"]["type"] == mode
        assert body["messages"][1]["content"][0]["image_url"]["url"] == "data:image/png;base64,fixture"
        assert "PageExtraction" in json.dumps(body)
        return httpx.Response(200, json=response())
    config = LLMConfig(model="vision", api_key="secret", response_format=mode)
    assert "secret" not in repr(config)
    result = JSONClient(config, httpx.MockTransport(handler)).request(PageExtraction, "Extract", [{"type": "image_url", "image_url": {"url": "data:image/png;base64,fixture"}}])
    assert len(result.components) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 429, 500, 302])
def test_provider_errors_are_redacted_and_redirects_not_followed(status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="secret proprietary drawing", headers={"Location": "https://other.example"})
    client = JSONClient(LLMConfig(model="vision", api_key="secret", retries=0), httpx.MockTransport(handler))
    with pytest.raises(LLMError) as caught:
        client.request(PageExtraction, "Extract", [])
    assert "secret" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.parametrize("body", [response(finish="length"), response(refusal="no"), {"choices": []}, {"choices": None}, {}, response({"schema_version": "1.0"})])
def test_bad_refused_or_truncated_responses_fail_closed(body):
    client = JSONClient(LLMConfig(model="vision", api_key="secret", retries=0), httpx.MockTransport(lambda _: httpx.Response(200, json=body)))
    with pytest.raises(LLMError):
        client.request(PageExtraction, "Extract", [])


@pytest.mark.parametrize("failure", [429, 503, "timeout"])
def test_transient_failure_retries_then_recovers(monkeypatch, failure):
    monkeypatch.setattr("schematic_mcp.llm.time.sleep", lambda _: None)
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("secret")
            return httpx.Response(failure)
        return httpx.Response(200, json=response())
    client = JSONClient(LLMConfig(model="vision", api_key="secret"), httpx.MockTransport(handler))
    assert client.request(PageExtraction, "Extract", []).coverage == "complete"
    assert len(calls) == 2


def test_retry_limit_and_no_leaked_timeout(monkeypatch):
    monkeypatch.setattr("schematic_mcp.llm.time.sleep", lambda _: None)
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret")
    client = JSONClient(LLMConfig(model="vision", api_key="secret", retries=1), httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="timed out"):
        client.request(PageExtraction, "Extract", [])
    assert len(calls) == 2


def test_oversized_response_rejected():
    client = JSONClient(LLMConfig(model="vision", api_key="secret", retries=0), httpx.MockTransport(lambda _: httpx.Response(200, content=b" " * (8 * 1024 * 1024 + 1))))
    with pytest.raises(LLMError, match="limit"):
        client.request(PageExtraction, "Extract", [])


def test_explicit_legacy_token_parameter():
    def handler(request):
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 16000
        assert "max_completion_tokens" not in payload
        return httpx.Response(200, json=response())
    config = LLMConfig(model="test", api_key="test", token_parameter="max_tokens")
    assert JSONClient(config, httpx.MockTransport(handler)).request(PageExtraction, "Extract", []).components
