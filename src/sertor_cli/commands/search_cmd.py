"""Comando `sertor search <query>` — interroga l'indice (REQ-020..023).

Politica esplicita di errore su indice mancante (REQ-022): se la collezione non esiste, solleva
`IndexNotFoundError` invece di restituire un risultato vuoto silenzioso. I default (k, modalità)
vengono dal core (REQ-021).
"""
from __future__ import annotations

from dataclasses import replace

from sertor_cli import output
from sertor_core.composition import build_embedder, build_store, collection_name
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import IndexNotFoundError
from sertor_core.services.retrieval import RetrievalFacade


def run(args) -> int:
    settings = Settings.load()
    if args.corpus:
        settings = replace(settings, corpus=args.corpus)
    embedder = build_embedder(settings)
    store = build_store(settings)
    collection = collection_name(settings, embedder)
    if not store.exists(collection):
        raise IndexNotFoundError(
            "indice inesistente: esegui prima `sertor index <path>`", collection=collection
        )

    facade = RetrievalFacade(embedder, store, collection, default_k=settings.default_k)
    mode = args.type or "both"
    if mode == "code":
        results = facade.search_code(args.query, k=args.k)
    elif mode == "doc":
        results = facade.search_docs(args.query, k=args.k)
    else:
        results = facade.search_combined(args.query, k=args.k)
    print(output.format_results(results, as_json=args.json, full=args.full))
    return 0
