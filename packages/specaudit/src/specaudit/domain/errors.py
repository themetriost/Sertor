"""Errori di dominio tipizzati (Constitution VI). Un errore per confine; lo stadio è identificabile.

Nessun `None` silenzioso, nessuna eccezione ingoiata: SpecAudit fallisce loud e nomina la causa.
"""

from __future__ import annotations


class SpecAuditError(Exception):
    """Radice di tutti gli errori di dominio di SpecAudit."""


# --- Confine: ingest dell'output SpecLift --------------------------------------------------


class SpecLiftArtifactError(SpecAuditError):
    """L'output SpecLift è assente o malformato (REQ-A04, FR-021)."""


class SpecLiftVersionError(SpecAuditError):
    """L'output SpecLift ha una versione di contratto non supportata (R5)."""


class ChangesetMismatchError(SpecAuditError):
    """L'output SpecLift si riferisce a un changeset diverso da quello richiesto (R5)."""


# --- Confine: adjudication dell'agente -----------------------------------------------------


class InvalidAdjudicationError(SpecAuditError):
    """L'adjudication è strutturalmente invalida (es. spiegazione mancante dove richiesta)."""


class DanglingReferenceError(InvalidAdjudicationError):
    """L'adjudication referenzia un indice inesistente nel bundle (R7)."""


class IncompleteAdjudicationError(InvalidAdjudicationError):
    """L'adjudication non copre ogni item esattamente una volta (R7, niente scarti silenziosi)."""
