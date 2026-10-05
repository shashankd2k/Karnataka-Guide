"""
Asynchronous Ollama LLM provider implementing ILLMProvider domain port.
Features persistent HTTP client connection pooling, strict timeouts, and streaming.
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
    Lightweight, persistent async client for local Ollama instances.
    Maintains a reusable connection pool with keep-alive, strict timeouts, and streaming.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        temperature: Optional[float] = None,
        keep_alive: Optional[str] = None,
        num_ctx: Optional[int] = None,
        num_thread: Optional[int] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS
        self.temperature = temperature if temperature is not None else settings.OLLAMA_TEMPERATURE
        self.keep_alive = keep_alive or settings.OLLAMA_KEEP_ALIVE
        self.num_ctx = num_ctx if num_ctx is not None else settings.OLLAMA_NUM_CTX
        self.num_thread = num_thread if num_thread is not None else getattr(settings, "OLLAMA_NUM_THREAD", 2)
        self._client: Optional[httpx.AsyncClient] = client

    def _get_client(self) -> httpx.AsyncClient:
        """Return or lazily initialize persistent httpx.AsyncClient with connection pooling."""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=600.0)
            self._client = httpx.AsyncClient(timeout=timeout, limits=limits)
        return self._client

    async def aclose(self) -> None:
        """Gracefully close persistent HTTP client connection pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OllamaLLMProvider":
        self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

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
        options = {
            "temperature": temp,
            "top_p": 0.9,
            "num_predict": max_tokens or 128,
            "num_ctx": self.num_ctx,
            "stop": ["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"],
        }
        if self.num_thread and self.num_thread > 0:
            options["num_thread"] = self.num_thread

        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": options,
        }

        url = f"{self.base_url}/api/generate"
        client = self._get_client()

        try:
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
        options = {
            "temperature": temp,
            "top_p": 0.9,
            "num_predict": max_tokens or 192,
            "num_ctx": self.num_ctx,
            "stop": ["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"],
        }
        if self.num_thread and self.num_thread > 0:
            options["num_thread"] = self.num_thread

        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": options,
        }

        url = f"{self.base_url}/api/generate"
        client = self._get_client()

        try:
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
        client = self._get_client()
        try:
            resp = await client.get(url, timeout=httpx.Timeout(5.0, connect=3.0))
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            target_base = self.model_name.split(":")[0]
            return target_base in models or self.model_name in [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return False


# Global singleton provider and lifecycle helper
_default_ollama_provider: Optional[OllamaLLMProvider] = None


def get_ollama_provider() -> OllamaLLMProvider:
    """Obtain or initialize the application-wide singleton Ollama provider."""
    global _default_ollama_provider
    if _default_ollama_provider is None:
        _default_ollama_provider = OllamaLLMProvider()
    return _default_ollama_provider


async def close_ollama_provider() -> None:
    """Cleanly close the global Ollama HTTP client pool on application shutdown."""
    global _default_ollama_provider
    if _default_ollama_provider is not None:
        await _default_ollama_provider.aclose()
        _default_ollama_provider = None
