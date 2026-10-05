"""
Asynchronous Ollama LLM provider implementing ILLMProvider domain port.
"""

import json
from typing import AsyncIterator, Optional
import httpx
import structlog
from app.core.config import get_settings
from app.core.errors import ServiceUnavailableException
from app.domain.ports.llm import ILLMProvider

logger = structlog.get_logger(__name__)


class OllamaLLMProvider(ILLMProvider):
    """
    Lightweight, native async client for local Ollama instances.
    Enforces strict timeout guards, low-temperature parameters, and streaming.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        temperature: Optional[float] = None,
        keep_alive: Optional[str] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS
        self.temperature = temperature if temperature is not None else settings.OLLAMA_TEMPERATURE
        self.keep_alive = keep_alive or settings.OLLAMA_KEEP_ALIVE

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a complete grounded text answer synchronously within the async event loop.
        """
        temp = temperature if temperature is not None else self.temperature
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temp,
                "top_p": 0.9,
                "num_predict": max_tokens or 128,
            },
        }

        url = f"{self.base_url}/api/generate"
        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    raise ServiceUnavailableException(
                        f"Configured Ollama model '{self.model_name}' was not found on local daemon."
                    )
                response.raise_for_status()
                data = response.json()
                answer = data.get("response", "").strip()
                return answer

        except httpx.ConnectError as exc:
            logger.error("ollama_connection_refused", url=url, error=str(exc))
            raise ServiceUnavailableException(
                f"Ollama local LLM daemon is unavailable at {self.base_url}. Please ensure Ollama is running."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("ollama_timeout", url=url, timeout=self.timeout_seconds)
            raise ServiceUnavailableException(
                f"Ollama LLM generation timed out after {self.timeout_seconds} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("ollama_http_error", status_code=exc.response.status_code, error=str(exc))
            raise ServiceUnavailableException(
                f"Ollama daemon returned HTTP {exc.response.status_code} error."
            ) from exc

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response tokens line-by-line from Ollama NDJSON output stream.
        """
        temp = temperature if temperature is not None else self.temperature
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temp,
                "top_p": 0.9,
                "num_predict": max_tokens or 512,
            },
        }

        url = f"{self.base_url}/api/generate"
        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code == 404:
                        raise ServiceUnavailableException(
                            f"Configured Ollama model '{self.model_name}' was not found on local daemon."
                        )
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

        except httpx.ConnectError as exc:
            logger.error("ollama_streaming_connection_refused", url=url, error=str(exc))
            raise ServiceUnavailableException(
                f"Ollama local LLM daemon is unavailable at {self.base_url}."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("ollama_streaming_timeout", url=url)
            raise ServiceUnavailableException("Ollama streaming connection timed out.") from exc

    async def check_health(self) -> bool:
        """
        Check if Ollama daemon is reachable and the configured model is installed.
        """
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return False
                data = resp.json()
                models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                target_base = self.model_name.split(":")[0]
                return target_base in models or self.model_name in [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return False
