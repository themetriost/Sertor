"""Configurazione centralizzata: legge `.env` ed espone i settaggi del workspace."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# `.env` autoritativo: vince su eventuali variabili d'ambiente del sistema
# (es. OLLAMA_HOST=0.0.0.0:11434 senza schema, che romperebbe il client HTTP).
load_dotenv(ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    backend: str = os.getenv("RAG_BACKEND", "local")
    # Corpus attivo del RAG: "fastapi" (demo del prototipo) | "sertor" (dogfooding sul prototipo stesso).
    # Selettore via env SERTOR_CORPUS (passato dal server MCP); MAI scritto in .env: con override=True
    # verrebbe congelato e il namespacing per corpus non cambierebbe più.
    corpus: str = os.getenv("SERTOR_CORPUS", "fastapi")

    # Ollama (locale)
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    # Modello chat/generativo locale (Agentic RAG): deve supportare il tool-calling.
    ollama_chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1")

    # Chunking del codice: "treesitter" (code-aware) | "recursive" (LangChain, size-driven)
    code_chunker: str = os.getenv("CODE_CHUNKER", "treesitter")

    # Azure OpenAI / Azure AI Foundry (endpoint v1)
    azure_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    azure_embed_small: str = os.getenv("AZURE_OPENAI_EMBED_SMALL_DEPLOYMENT", "")
    azure_embed_large: str = os.getenv("AZURE_OPENAI_EMBED_LARGE_DEPLOYMENT", "")
    azure_chat: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")

    # Percorsi
    root: Path = ROOT
    raw_dir: Path = ROOT / "raw"
    fastapi_dir: Path = ROOT / "raw" / "fastapi"
    # Indici namespaced per corpus (calcolati in __post_init__): ".index" per fastapi,
    # ".index-<corpus>" altrimenti. I default qui valgono per il corpus fastapi.
    index_dir: Path = ROOT / "01-baseline" / ".index"
    graph_path: Path = ROOT / "03-graphrag" / ".index" / "code_graph.graphml"

    def __post_init__(self):
        # Garantisce uno schema sull'host Ollama (httpx richiede http://).
        if self.ollama_host and not self.ollama_host.startswith(("http://", "https://")):
            object.__setattr__(self, "ollama_host", f"http://{self.ollama_host}")
        # Namespacing degli indici per corpus: NON distruttivo (fastapi resta in `.index`,
        # il dogfooding "sertor" va in `.index-sertor`, in una directory separata).
        suffix = "" if self.corpus == "fastapi" else f"-{self.corpus}"
        object.__setattr__(self, "index_dir", ROOT / "01-baseline" / f".index{suffix}")
        object.__setattr__(self, "graph_path",
                           ROOT / "03-graphrag" / f".index{suffix}" / "code_graph.graphml")


settings = Settings()
