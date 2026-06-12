"""Adapter `LexicalIndex` su BM25 (rank-bm25) con sidecar JSON persistito (FEAT-004, gruppo A).

Il sidecar vive nella stessa directory di indici namespaced dello store vettoriale
(`<index_dir>/lexical/<collection>.json`, REQ-072): il nome collezione codifica già
`(corpus, provider)` → namespacing gratis (REQ-005). Persistere un artefatto rende
**rilevabile l'assenza** dell'indice (corpus pre-ibrido), condizione della degradazione
REQ-034 — la policy resta del motore, qui solo `exists()`.

Il testo è memorizzato grezzo e tokenizzato al caricamento; l'indice BM25 è costruito
in memoria una volta per collezione e cache-ato nell'istanza (corpora tipici < 10k chunk).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from sertor_core.domain.entities import LexicalEntry
from sertor_core.domain.errors import ConfigError
from sertor_core.domain.ports import DocTypeFilter

_FORMAT = "sertor.lexical/1"
_TOKENIZER_VERSION = 1
_WORD = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Token lowercase; per gli snake_case aggiunge anche i sotto-token (REQ-001).

    È il differenziatore sulle query a simbolo esatto (parità col prototipo 02).
    """
    out: list[str] = []
    for word in _WORD.findall(text.lower()):
        out.append(word)
        if "_" in word:
            out.extend(part for part in word.split("_") if part)
    return out


class Bm25LexicalIndex:
    """`LexicalIndex` su BM25Okapi + sidecar JSON atomico."""

    def __init__(self, index_dir: Path | str):
        self._dir = Path(index_dir) / "lexical"
        # cache per collezione: (entries, bm25, token_sets) — invalidata da build/reset.
        self._cache: dict[str, tuple[list[LexicalEntry], object, list[set[str]]]] = {}

    def _sidecar(self, collection: str) -> Path:
        return self._dir / f"{collection}.json"

    def build(self, collection: str, entries: list[LexicalEntry]) -> None:
        """Sostituisce integralmente il sidecar (snapshot intero, idempotente, atomico)."""
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": _FORMAT,
            "tokenizer_version": _TOKENIZER_VERSION,
            "collection": collection,
            "entries": [
                {"chunk_id": e.chunk_id, "path": e.path, "doc_type": e.doc_type, "text": e.text}
                for e in entries
            ],
        }
        # Scrittura atomica: tmp nella stessa directory + replace (mai sidecar troncato).
        fd, tmp_name = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(tmp_name, self._sidecar(collection))
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        self._cache.pop(collection, None)

    def _load(self, collection: str) -> tuple[list[LexicalEntry], object, list[set[str]]]:
        if collection in self._cache:
            return self._cache[collection]
        path = self._sidecar(collection)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"sidecar lessicale corrotto: {path} — ricostruirlo con un re-index",
            ) from exc
        if data.get("format") != _FORMAT:
            raise ConfigError(
                f"formato del sidecar lessicale non riconosciuto ({data.get('format')!r}): "
                f"{path} — ricostruirlo con un re-index",
            )
        entries = [
            LexicalEntry(item["chunk_id"], item["text"], item["doc_type"], item["path"])
            for item in data.get("entries", [])
        ]
        bm25 = None
        token_sets: list[set[str]] = []
        if entries:
            from rank_bm25 import BM25Okapi

            tokenized = [tokenize(e.text) or [""] for e in entries]
            bm25 = BM25Okapi(tokenized)
            token_sets = [set(tokens) for tokens in tokenized]
        self._cache[collection] = (entries, bm25, token_sets)
        return self._cache[collection]

    def query(
        self,
        collection: str,
        query: str,
        k: int,
        doc_type: DocTypeFilter = "both",
    ) -> list[str]:
        if k <= 0:
            return []
        entries, bm25, token_sets = self._load(collection)
        if not entries or bm25 is None:
            return []
        query_tokens = tokenize(query)
        query_set = set(query_tokens)
        scores = bm25.get_scores(query_tokens)
        # Candidato = contiene almeno un token della query. Il rank arriva dallo score BM25 anche
        # se ≤ 0: con corpora piccoli l'IDF Okapi dei termini molto comuni è negativo (epsilon
        # floor di rank_bm25) e un filtro "score > 0" scarterebbe match legittimi.
        scored = [
            (float(score), entry.chunk_id)
            for score, entry, tokens in zip(scores, entries, token_sets, strict=True)
            if tokens & query_set and (doc_type == "both" or entry.doc_type == doc_type)
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))  # pareggi per chunk_id (REQ-012)
        return [chunk_id for _, chunk_id in scored[:k]]

    def lookup(self, collection: str, chunk_ids: list[str]) -> list[LexicalEntry]:
        entries, _, _ = self._load(collection)
        by_id = {e.chunk_id: e for e in entries}
        return [by_id[cid] for cid in chunk_ids if cid in by_id]

    def exists(self, collection: str) -> bool:
        return self._sidecar(collection).exists()

    def reset(self, collection: str) -> None:
        self._sidecar(collection).unlink(missing_ok=True)  # assente = no-op (idempotente)
        self._cache.pop(collection, None)
