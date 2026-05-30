"""Chat/completion layer intercambiabile (Ollama + Azure) con tool-calling.

È il gemello generativo di `shared/embeddings.py`: stessa filosofia local-first con
switch via `RAG_BACKEND`. Espone un'interfaccia uniforme `chat(messages, tools)` che
normalizza i `tool_calls` dei due provider in una forma comune, così l'orchestratore
(Tappa 04) è indipendente sia dal provider sia dal framework.

- local  → Ollama  (`/api/chat`, modello `OLLAMA_CHAT_MODEL`, tool-capable)
- azure  → Azure OpenAI (endpoint v1 `/chat/completions`, deployment `AZURE_OPENAI_CHAT_DEPLOYMENT`)

Il formato degli schemi-tool è quello OpenAI/Ollama (`{"type":"function","function":{...}}`),
identico per entrambi i provider.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from shared.config import settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall]
    raw: dict  # messaggio assistant grezzo del provider, da riaccodare ai `messages`


class ChatClient:
    name: str

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             temperature: float = 0.0) -> ChatResponse:
        raise NotImplementedError

    def tool_result_message(self, call: ToolCall, content: str) -> dict:
        """Messaggio `role=tool` da accodare con il risultato dell'esecuzione del tool."""
        raise NotImplementedError


class OllamaChat(ChatClient):
    def __init__(self, host: str, model: str):
        self.name = f"ollama:{model}"
        self.host = host.rstrip("/")
        self.model = model

    def chat(self, messages, tools=None, temperature=0.0):
        body = {"model": self.model, "messages": messages, "stream": False,
                "options": {"temperature": temperature}}
        if tools:
            body["tools"] = tools
        r = httpx.post(f"{self.host}/api/chat", json=body, timeout=600)
        r.raise_for_status()
        msg = r.json()["message"]
        calls = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc["function"]
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args or "{}")
            calls.append(ToolCall(id=tc.get("id") or f"call_{i}", name=fn["name"], arguments=args))
        return ChatResponse(content=msg.get("content") or "", tool_calls=calls, raw=msg)

    def tool_result_message(self, call, content):
        return {"role": "tool", "content": content}


class AzureChat(ChatClient):
    def __init__(self, endpoint: str, api_key: str, deployment: str):
        self.name = f"azure:{deployment}"
        self.url = endpoint.rstrip("/") + "/chat/completions"
        self.key = api_key
        self.deployment = deployment

    def chat(self, messages, tools=None, temperature=0.0):
        body = {"model": self.deployment, "messages": messages, "temperature": temperature}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        r = httpx.post(self.url, headers={"api-key": self.key}, json=body, timeout=600)
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc["function"]
            args = fn.get("arguments") or "{}"
            if isinstance(args, str):
                args = json.loads(args or "{}")
            calls.append(ToolCall(id=tc.get("id") or fn["name"], name=fn["name"], arguments=args))
        return ChatResponse(content=msg.get("content") or "", tool_calls=calls, raw=msg)

    def tool_result_message(self, call, content):
        return {"role": "tool", "tool_call_id": call.id, "content": content}


def get_chat_client(backend: str | None = None) -> ChatClient:
    """Client chat per il backend richiesto (default: `settings.backend`)."""
    s = settings
    backend = backend or s.backend
    if backend == "azure":
        if not (s.azure_endpoint and s.azure_key and s.azure_chat):
            raise RuntimeError(
                "Backend azure: configurare AZURE_OPENAI_ENDPOINT / _API_KEY / _CHAT_DEPLOYMENT in .env"
            )
        return AzureChat(s.azure_endpoint, s.azure_key, s.azure_chat)
    return OllamaChat(s.ollama_host, s.ollama_chat_model)
