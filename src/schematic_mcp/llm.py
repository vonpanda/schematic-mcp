"""Bounded, explicit OpenAI-compatible JSON requests. No implicit network calls."""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Safe to expose: never includes credentials, provider bodies or image data."""


@dataclass(frozen=True)
class LLMConfig:
    model: str
    api_key: str = field(repr=False)
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 120.0
    retries: int = 2
    max_tokens: int = 16000
    response_format: str = "json_schema"
    token_parameter: str = "max_completion_tokens"

    def __post_init__(self) -> None:
        url = urlsplit(self.base_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (url.scheme != "https" and not (url.scheme == "http" and local)) or not url.hostname:
            raise ValueError("LLM base URL must use HTTPS (HTTP allowed only on loopback)")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("LLM base URL must not contain credentials, query or fragment")
        if not self.model.strip() or not self.api_key.strip():
            raise ValueError("Set SCHEMATIC_LLM_MODEL and SCHEMATIC_LLM_API_KEY")
        if not math.isfinite(self.timeout) or not 1 <= self.timeout <= 600:
            raise ValueError("LLM timeout must be between 1 and 600 seconds")
        if not 0 <= self.retries <= 3 or not 256 <= self.max_tokens <= 64000:
            raise ValueError("Invalid LLM retry or output token limit")
        if self.token_parameter not in {"max_completion_tokens", "max_tokens"}:
            raise ValueError("LLM token parameter must be max_completion_tokens or max_tokens")
        if self.response_format not in {"json_schema", "json_object"}:
            raise ValueError("LLM response format must be json_schema or json_object")

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls(
            model=os.getenv("SCHEMATIC_LLM_MODEL", ""),
            api_key=os.getenv("SCHEMATIC_LLM_API_KEY", ""),
            base_url=os.getenv("SCHEMATIC_LLM_BASE_URL", "https://api.openai.com/v1"),
            timeout=float(os.getenv("SCHEMATIC_LLM_TIMEOUT", "120")),
            retries=int(os.getenv("SCHEMATIC_LLM_RETRIES", "2")),
            max_tokens=int(os.getenv("SCHEMATIC_LLM_MAX_TOKENS", "16000")),
            token_parameter=os.getenv("SCHEMATIC_LLM_TOKEN_PARAMETER", "max_completion_tokens"),
            response_format=os.getenv("SCHEMATIC_LLM_RESPONSE_FORMAT", "json_schema"),
        )


class JSONClient:
    def __init__(self, config: LLMConfig, transport: httpx.BaseTransport | None = None):
        self.config = config
        self.transport = transport
        self.usage: list[dict[str, Any]] = []

    def request(self, schema: type[T], system: str, content: list[dict[str, Any]]) -> T:
        definition = schema.model_json_schema()
        response_format: dict[str, Any] = {"type": self.config.response_format}
        if self.config.response_format == "json_schema":
            response_format["json_schema"] = {"name": schema.__name__, "strict": True, "schema": definition}
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system + "\nReturn only JSON matching this schema:\n" + json.dumps(definition)},
                {"role": "user", "content": content},
            ],
            "response_format": response_format,
            self.config.token_parameter: self.config.max_tokens,
        }
        # Redirects could send customer content or credentials to another host.
        with httpx.Client(timeout=self.config.timeout, follow_redirects=False, transport=self.transport) as client:
            for attempt in range(self.config.retries + 1):
                try:
                    with client.stream(
                        "POST", self.config.base_url.rstrip("/") + "/chat/completions",
                        headers={"Authorization": "Bearer " + self.config.api_key}, json=payload,
                    ) as response:
                        status = response.status_code
                        if status in {429, 500, 502, 503, 504} and attempt < self.config.retries:
                            time.sleep(min(2 ** attempt, 4))
                            continue
                        if status != 200:
                            raise LLMError(f"LLM returned HTTP {status}; check provider configuration/quota")
                        body = bytearray()
                        for chunk in response.iter_bytes():
                            body.extend(chunk)
                            if len(body) > 8 * 1024 * 1024:
                                raise LLMError("LLM response exceeds 8 MiB limit")
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt < self.config.retries:
                        time.sleep(min(2 ** attempt, 4))
                        continue
                    raise LLMError("LLM network request failed or timed out") from None
                except httpx.HTTPError:
                    raise LLMError("LLM transport failed") from None
                try:
                    data = json.loads(body)
                    choice = data["choices"][0]
                    if choice["finish_reason"] != "stop":
                        raise LLMError("LLM output incomplete; increase output limit or use a smaller document")
                    if choice["message"].get("refusal"):
                        raise LLMError("LLM refused the extraction/review request")
                    result = schema.model_validate_json(choice["message"]["content"])
                    usage = data.get("usage", {})
                    self.usage.append({k: v for k, v in usage.items() if k in {"prompt_tokens", "completion_tokens", "total_tokens"} and type(v) is int})
                    return result
                except (KeyError, IndexError, TypeError, ValueError, AttributeError, ValidationError):
                    raise LLMError("LLM returned invalid JSON or data that failed schema validation") from None
        raise LLMError("LLM request exhausted retries")
