"""Adapter LLM per Ollama (provider locale). Implementa la porta `LLMProvider` via `/api/chat`."""
from __future__ import annotations

import httpx

from sertor_core.domain.errors import SertorError


class OllamaLLM:
    """`LLMProvider` su Ollama. `client` iniettabile per i test (NFR/testabilità)."""

    def __init__(self, host: str, model: str, client: httpx.Client | None = None):
        self.name = f"ollama:{model}"
        self._host = host.rstrip("/")
        self._model = model
        self._client = client or httpx.Client(timeout=300)

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            r = self._client.post(
                f"{self._host}/api/chat",
                json={"model": self._model, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            return r.json()["message"]["content"]
        except httpx.HTTPError as exc:
            raise SertorError(f"LLM Ollama non raggiungibile: {type(exc).__name__}") from exc
