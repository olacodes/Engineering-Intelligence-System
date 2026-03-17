"""Embedding provider abstractions and concrete implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import json
import math
import ssl
import socket
import time
from typing import Any
from urllib import error, request


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text input."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of text inputs."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embeddings provider using HTTP requests.

    This works with OpenAI and any OpenAI-compatible endpoint that supports
    ``POST /v1/embeddings``.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-large",
        base_url: str = "https://api.openai.com",
        timeout_seconds: int = 30,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key is required for OpenAIEmbeddingProvider")

        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload: dict[str, Any] = {"model": self._model, "input": texts}
        endpoint = f"{self._base_url}/v1/embeddings"
        body = json.dumps(payload).encode("utf-8")

        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        # Retry on transient network/SSL errors
        max_attempts = 3
        backoff_base = 1
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                with request.urlopen(
                    http_request, timeout=self._timeout_seconds
                ) as response:
                    data = json.loads(response.read().decode("utf-8"))
                last_exc = None
                break
            except error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"embedding request failed with status {exc.code}: {details}"
                ) from exc
            except (
                error.URLError,
                ssl.SSLError,
                socket.timeout,
                ConnectionResetError,
            ) as exc:
                last_exc = exc
                if attempt < max_attempts:
                    sleep_for = backoff_base * (2 ** (attempt - 1))
                    time.sleep(sleep_for)
                    continue
                raise RuntimeError(
                    "embedding request failed due to network/SSL error after "
                    f"{max_attempts} attempts: {exc}. Check network, proxy, or TLS settings."
                ) from exc

        raw_items = data.get("data", [])
        vectors = [item["embedding"] for item in raw_items]

        if len(vectors) != len(texts):
            raise RuntimeError(
                "embedding provider returned mismatched vector count "
                f"(expected {len(texts)}, got {len(vectors)})"
            )

        return [[float(value) for value in vector] for vector in vectors]


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Offline-safe deterministic provider useful for tests and examples."""

    def __init__(self, dimension: int = 64) -> None:
        if dimension < 8:
            raise ValueError("dimension must be at least 8")
        self._dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(text) for text in texts]

    def _embed_single(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []

        while len(values) < self._dimension:
            for byte in digest:
                if len(values) >= self._dimension:
                    break
                normalized = (byte / 255.0) * 2.0 - 1.0
                values.append(normalized)
            digest = hashlib.sha256(digest).digest()

        # L2 normalize for vector-db friendly behavior.
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return values
        return [value / norm for value in values]
