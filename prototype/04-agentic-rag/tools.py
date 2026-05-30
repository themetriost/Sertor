"""Tool dell'Agentic RAG: schemi per il function-calling + dispatch verso i motori.

Layer **condiviso da tutti i framework** (orchestratore vanilla, AutoGen, SK, LangGraph):
gli stessi tool e lo stesso system prompt, così il confronto tra framework è a parità di
strumenti. I tool sono sottili wrapper su `shared.retrieval`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # root -> shared

from shared import retrieval  # noqa: E402

# Schemi in formato OpenAI/Ollama (identico per i due provider).
TOOLS: list[dict] = [
    {"type": "function", "function": {
        "name": "search_code",
        "description": "Cerca nel CODICE sorgente (hybrid BM25+dense). Usalo per trovare "
                       "implementazioni, funzioni, classi o dove qualcosa è usato nel codice.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "query in linguaggio naturale o un identificatore/simbolo"},
            "k": {"type": "integer", "description": "numero di risultati (default 5)"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "search_docs",
        "description": "Cerca nella DOCUMENTAZIONE (Markdown). Usalo per spiegazioni concettuali, "
                       "guide, tutorial, comportamento atteso.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "domanda in linguaggio naturale"},
            "k": {"type": "integer", "description": "numero di risultati (default 5)"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "search_combined",
        "description": "Cerca su CODICE + DOC insieme con reranking. Usalo quando la domanda "
                       "richiede sia l'implementazione sia la spiegazione.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "domanda in linguaggio naturale"},
            "k": {"type": "integer", "description": "numero di risultati (default 6)"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "find_symbol",
        "description": "Dove è DEFINITO un simbolo (classe/funzione/metodo), con path:lineno.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "nome esatto del simbolo, es. OAuth2PasswordBearer"}},
            "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "who_calls",
        "description": "Chi CHIAMA un simbolo (chiamanti nel call graph).",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "nome esatto del simbolo"}},
            "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "related_docs",
        "description": "Documenti Markdown che MENZIONANO un simbolo.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "nome esatto del simbolo"}},
            "required": ["name"]}}},
]

_DISPATCH = {
    "search_code": lambda a: retrieval.search_code(a["query"], int(a.get("k", 5))),
    "search_docs": lambda a: retrieval.search_docs(a["query"], int(a.get("k", 5))),
    "search_combined": lambda a: retrieval.search_combined(a["query"], int(a.get("k", 6))),
    "find_symbol": lambda a: retrieval.find_symbol(a["name"]),
    "who_calls": lambda a: retrieval.who_calls(a["name"]),
    "related_docs": lambda a: retrieval.related_docs(a["name"]),
}


def _stringify(result) -> str:
    if isinstance(result, list):
        if not result:
            return "(nessun risultato)"
        if isinstance(result[0], dict):
            return "\n".join(
                f"- [{r.get('source')}/{r.get('kind')}] {r['path']}#{r.get('chunk')}: {r.get('preview', '')}"
                for r in result)
        return "\n".join(f"- {r}" for r in result)
    return str(result)


def call_tool(name: str, arguments: dict) -> str:
    """Esegue un tool e restituisce il risultato come stringa per l'LLM (errori inclusi)."""
    if name not in _DISPATCH:
        return f"(tool sconosciuto: {name})"
    try:
        return _stringify(_DISPATCH[name](arguments or {}))
    except Exception as e:  # noqa: BLE001 — l'errore torna all'LLM, che può ripiegare
        return f"(errore nel tool {name}: {e})"


SYSTEM_PROMPT = (
    "Sei un assistente di retrieval su una codebase (FastAPI) che contiene codice e "
    "documentazione. Hai strumenti per cercare nel codice, nella documentazione e nel "
    "grafo dei simboli.\n"
    "Strategia: scomponi la domanda in sotto-obiettivi, scegli gli strumenti giusti, "
    "itera se il contesto recuperato non basta, infine sintetizza una risposta CITANDO "
    "sempre i file (path#chunk oppure path:lineno).\n"
    "Linee guida: usa search_code per implementazioni/simboli, search_docs per spiegazioni "
    "concettuali, search_combined quando servono entrambi; find_symbol/who_calls/related_docs "
    "per navigare le relazioni del codice. Non inventare: se non trovi nulla, dichiaralo."
)
