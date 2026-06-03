"""Eccezioni di dominio del nucleo (Principio IV: errori espliciti, niente None silenzioso).

Gli errori di terze parti (SDK di provider/store) vanno **avvolti** in queste eccezioni al
boundary degli adapter, così il core non espone tipi esterni. Un'assenza lecita (file
illeggibile, indice vuoto) NON è un errore: si gestisce con warning + prosecuzione / risultato
vuoto, non sollevando queste eccezioni.
"""
from __future__ import annotations


class SertorError(Exception):
    """Radice di tutte le eccezioni di dominio Sertor."""


class ConfigError(SertorError):
    """Configurazione mancante o incoerente."""

    def __init__(self, message: str, *, key: str | None = None):
        self.key = key
        super().__init__(message if key is None else f"{message} (chiave: {key})")


class IngestionError(SertorError):
    """La radice del repository non è accessibile o non è una directory valida."""

    def __init__(self, message: str, *, path: str | None = None):
        self.path = path
        super().__init__(message if path is None else f"{message} (path: {path})")


class EmbeddingError(SertorError):
    """Il provider di embeddings non è disponibile o ha restituito un errore (REQ-015).

    Identifica provider, causa e ritentabilità per consentire al chiamante una decisione.
    """

    def __init__(self, message: str, *, provider: str, reason: str, retriable: bool):
        self.provider = provider
        self.reason = reason
        self.retriable = retriable
        super().__init__(
            f"{message} [provider={provider}, reason={reason}, retriable={retriable}]"
        )


class VectorStoreError(SertorError):
    """Il backend di vector store non è disponibile (REQ-021).

    Sollevato invece di restituire silenziosamente risultati vuoti.
    """

    def __init__(self, message: str, *, backend: str, reason: str):
        self.backend = backend
        self.reason = reason
        super().__init__(f"{message} [backend={backend}, reason={reason}]")


class IndexNotFoundError(SertorError):
    """Si interroga un indice che non esiste ancora (REQ-009 di FEAT-002).

    A livello di motore l'assenza dell'indice è un errore d'uso esplicito (costruire l'indice
    prima di interrogare), non un risultato vuoto silenzioso.
    """

    def __init__(self, message: str, *, collection: str):
        self.collection = collection
        super().__init__(f"{message} [collection={collection}]")
