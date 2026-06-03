"""Adapter LLM per Azure OpenAI (provider cloud). Implementa `LLMProvider` via `/chat/completions`.

Credenziali dalla config centralizzata, mai loggate (REQ-E5).
"""
from __future__ import annotations

import httpx

from sertor_core.domain.errors import SertorError


class AzureLLM:
    """`LLMProvider` su Azure OpenAI. `client` iniettabile per i test."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-10-21",
        client: httpx.Client | None = None,
    ):
        if not endpoint or not api_key or not deployment:
            raise SertorError("configurazione Azure LLM incompleta (endpoint/api_key/deployment)")
        self.name = f"azure:{deployment}"
        self._url = endpoint.rstrip("/") + "/chat/completions"
        self._key = api_key
        self._deployment = deployment
        self._api_version = api_version
        self._v1 = "/openai/v1" in endpoint  # superficie v1: niente api-version
        self._client = client or httpx.Client(timeout=300)

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            r = self._client.post(
                self._url,
                params=None if self._v1 else {"api-version": self._api_version},
                headers={"api-key": self._key},
                json={"model": self._deployment, "messages": messages},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise SertorError(f"LLM Azure non raggiungibile: {type(exc).__name__}") from exc
