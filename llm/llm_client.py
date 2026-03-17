"""Reusable Claude API client for EIS reasoning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import error as urlerror
from urllib import request as urlrequest

from config import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

MODEL_FALLBACK_CANDIDATES = [
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]


class ClaudeAPIError(RuntimeError):
    """Raised when Claude API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMClient(Protocol):
    """Protocol for text generation clients used by reasoning service."""

    def generate(self, prompt: str) -> str:
        """Generate completion text for the supplied prompt."""


@dataclass
class ClaudeClient:
    """Minimal Claude Messages API client using stdlib HTTP primitives."""

    api_key: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 1200
    temperature: float = 0.1
    timeout_seconds: int = 60
    api_url: str = "https://api.anthropic.com/v1/messages"

    @classmethod
    def from_settings(cls, settings: Settings) -> "ClaudeClient":
        """Build a Claude client instance from application settings."""
        if not settings.llm_api_key:
            raise ValueError("LLM API key is required to initialize ClaudeClient")

        return cls(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout,
        )

    def generate(self, prompt: str) -> str:
        """Call Claude Messages API and return plain model text."""
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")

        candidate_models = [self.model] + [
            model for model in MODEL_FALLBACK_CANDIDATES if model != self.model
        ]

        last_error: ClaudeAPIError | None = None
        for model in candidate_models:
            try:
                return self._generate_with_model(prompt=prompt, model=model)
            except ClaudeAPIError as exc:
                last_error = exc
                # Retry only on model-not-found responses.
                if exc.status_code == 404:
                    logger.warning(
                        "Claude model '%s' unavailable; trying fallback model",
                        model,
                    )
                    continue
                raise

        raise ClaudeAPIError(
            "Claude API model resolution failed. Tried models: "
            + ", ".join(candidate_models)
        ) from last_error

    def _generate_with_model(self, prompt: str, model: str) -> str:
        """Call Claude Messages API for a specific model identifier."""

        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        req = urlrequest.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            with urlrequest.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            logger.error("Claude API HTTP error %s: %s", exc.code, error_body)

            if exc.code == 404:
                raise ClaudeAPIError(
                    "Claude API returned 404. Verify LLM model name and endpoint configuration "
                    f"(model='{model}', url='{self.api_url}').",
                    status_code=exc.code,
                ) from exc

            raise ClaudeAPIError(
                f"Claude API request failed with status {exc.code}",
                status_code=exc.code,
            ) from exc
        except urlerror.URLError as exc:
            logger.error("Claude API network error: %s", exc.reason)
            raise ClaudeAPIError(
                "Claude API request failed due to network error"
            ) from exc

        data = json.loads(body)
        content = data.get("content", [])
        parts = [part.get("text", "") for part in content if part.get("type") == "text"]
        result = "\n".join(part.strip() for part in parts if part.strip()).strip()

        if not result:
            raise ClaudeAPIError("Claude API returned an empty response")

        return result
