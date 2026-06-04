"""Mock delle porte di dominio per i test del core, senza cloud né rete (NFR-01).

`FakeEmbedder` è deterministico (stesso testo → stesso vettore) per esercitare l'idempotenza;
`InMemoryStore` implementa `VectorStore` con similarità coseno in memoria.
"""
from __future__ import annotations

import hashlib
import math

from sertor_core.domain.entities import DocType, EmbeddedChunk, RetrievalResult


class FakeEmbedder:
    """Provider di embeddings finto e deterministico (dim piccola)."""

    def __init__(self, dim: int = 8, batch_size: int = 64):
        self.name = f"fake:{dim}"
        self.dim = dim
        self.batch_size = batch_size
        self.calls = 0

    def _vector(self, text: str) -> list[float]:
        out: list[float] = []
        i = 0
        # Espande un digest deterministico fino a `dim` componenti.
        while len(out) < self.dim:
            h = hashlib.sha256(f"{i}:{text}".encode()).digest()
            for b in h:
                out.append(b / 255.0)
                if len(out) >= self.dim:
                    break
            i += 1
        return out

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self.calls += 1
        return [self._vector(t) for t in texts]


class FakeLLM:
    """Provider LLM finto e deterministico per i test della distillazione."""

    def __init__(self):
        self.name = "fake-llm"
        self.calls = 0

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.calls += 1
        return f"Sintesi distillata.\n\n{prompt.strip()}"


class ScriptedLLM:
    """Provider LLM scriptato e deterministico: restituisce risposte in sequenza.

    Le risposte sono consumate in ordine; esaurita la lista, ripete l'ultima (o `"[]"` se vuota).
    Registra `calls` e i `prompts` ricevuti per le asserzioni dei test (nessuna rete).
    """

    def __init__(self, responses: list[str] | None = None, name: str = "scripted-llm"):
        self.name = name
        self.responses = list(responses or [])
        self.calls = 0
        self.prompts: list[str] = []

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.prompts.append(prompt)
        idx = self.calls
        self.calls += 1
        if not self.responses:
            return "[]"
        if idx < len(self.responses):
            return self.responses[idx]
        return self.responses[-1]  # esaurite: ripete l'ultima


class FakeGit:
    """`GitPort` deterministico e scope-aware per i test (nessun processo, nessuna rete).

    `changed` può essere un dict `scope -> list[path]` (granularità per scope) o una lista unica
    valida per ogni scope. `head` è lo SHA di HEAD; `renames` le coppie `(old, new)`.
    """

    def __init__(
        self,
        *,
        changed: dict[str, list[str]] | list[str] | None = None,
        head: str | None = "deadbeef",
        renames: list[tuple[str, str]] | None = None,
    ):
        self._changed = changed
        self._head = head
        self._renames = list(renames or [])

    def changed_paths(self, scope: str, watermark: str | None = None) -> list[str]:
        if self._changed is None:
            return []
        if isinstance(self._changed, dict):
            return list(self._changed.get(scope, []))
        return list(self._changed)  # lista unica: vale per ogni scope

    def head_commit(self) -> str | None:
        return self._head

    def renamed_paths(self) -> list[tuple[str, str]]:
        return list(self._renames)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class InMemoryStore:
    """Vector store in memoria con similarità coseno; namespacing per collezione."""

    def __init__(self) -> None:
        # collection -> {chunk_id: (vector, payload)}
        self._data: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        coll = self._data.setdefault(collection, {})
        for r in records:
            coll[r.chunk_id] = (r.vector, r.payload)  # idempotente: sostituisce sugli stessi id

    def query(
        self,
        collection: str,
        vector: list[float],
        k: int,
        doc_type: str = "both",
    ) -> list[RetrievalResult]:
        coll = self._data.get(collection)
        if not coll:
            return []
        scored: list[tuple[float, str, dict]] = []
        for cid, (vec, payload) in coll.items():
            if doc_type != "both" and payload.get("doc_type") != doc_type:
                continue
            scored.append((_cosine(vector, vec), cid, payload))
        scored.sort(key=lambda t: t[0], reverse=True)
        results: list[RetrievalResult] = []
        for score, cid, payload in scored[: max(0, k)]:
            results.append(
                RetrievalResult(
                    text=payload.get("text", ""),
                    path=payload.get("path", ""),
                    chunk_id=cid,
                    doc_type=DocType(payload.get("doc_type", "code")),
                    score=score,
                    metadata=payload.get("metadata"),
                )
            )
        return results

    def delete(self, collection: str, ids: list[str]) -> None:
        coll = self._data.get(collection)
        if not coll:
            return
        for cid in ids:
            coll.pop(cid, None)

    def reset(self, collection: str) -> None:
        self._data.pop(collection, None)   # rebuild-from-scratch (idempotente)

    def exists(self, collection: str) -> bool:
        return bool(self._data.get(collection))
