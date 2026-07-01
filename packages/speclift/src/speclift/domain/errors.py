"""Errori di dominio tipizzati (Constitution VI). Uno per confine; nessun `None` silenzioso.

L'`exit_code` di ciascun errore mappa il contratto CLI (`contracts/cli.md`).
"""

from __future__ import annotations


class SpecLiftError(Exception):
    """Base di tutti gli errori di dominio. `exit_code` è il codice di uscita CLI associato."""

    exit_code: int = 1


class InvalidRefError(SpecLiftError):
    """Il riferimento git non risolve a un diff valido (fail-loud)."""

    exit_code = 2


class RagUnavailableError(SpecLiftError):
    """Il Sertor RAG non è disponibile / indice mancante o stantio (fail-loud)."""

    exit_code = 3


class EarsAuthorUnavailableError(SpecLiftError):
    """La capacità `requirements` (stesura EARS) non è disponibile (fail-loud)."""

    exit_code = 4


class BundleContractError(SpecLiftError):
    """Bundle o output non conforme al contratto/schema."""

    exit_code = 5
