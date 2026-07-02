"""Configurazione centralizzata (Constitution IX).

Tutte le soglie e le policy stanno qui, lette una volta e iniettate; cambiare un'opzione è un
cambio di configurazione, non un'edit sparsa nel codice.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Contratti versionati ------------------------------------------------------------------

BUNDLE_VERSION = "1"
REPORT_VERSION = "1"

# Versione dell'output SpecLift che sappiamo consumare (output.schema.json di SpecLift).
SUPPORTED_SPECLIFT_VERSION = "1"

# --- Scala categorica ----------------------------------------------------------------------

# Ordinamento delle categorie (per confronti/clamp e per ordinare i record per rischio).
LEVEL_ORDER: dict[str, int] = {"bassa": 0, "media": 1, "alta": 2}

# Ordine di gravità dei verdetti (worst-wins e ordinamento). Più alto = peggiore.
VERDICT_SEVERITY_ORDER: dict[str, int] = {
    "SODDISFATTO": 0,
    "NON_DOCUMENTATO": 1,
    "MANCANTE": 2,
    "PARZIALE": 3,
    "DRIFTED": 4,
}

# --- Matrice di rischio: severità × rilevabilità → rischio ----------------------------------
#
# Lo scoring è LEGGERO e categorico (decisione clarify 2026-07-02): non è un FMEA.
# Interpretazione della rilevabilità: BASSA rilevabilità = difficile da notare a mano → più
# rischioso (un problema grave che sfugge pesa di più).


def _risk(severity: str, detectability: str) -> str:
    """Combina severità e (in)rilevabilità in un livello di rischio categorico.

    Rischio alto quando la severità è alta E la rilevabilità è bassa (grave e nascosto).
    """
    sev = LEVEL_ORDER[severity]
    # invertiamo la rilevabilità: bassa rilevabilità → contributo alto al rischio
    hidden = 2 - LEVEL_ORDER[detectability]
    score = sev + hidden  # 0..4
    if score >= 3:
        return "alta"
    if score == 2:
        return "media"
    return "bassa"


@dataclass(frozen=True)
class Config:
    """Configurazione runtime di SpecAudit."""

    bundle_version: str = BUNDLE_VERSION
    report_version: str = REPORT_VERSION
    supported_speclift_version: str = SUPPORTED_SPECLIFT_VERSION

    # Cascata di risoluzione della fonte originale (ordine di affidabilità decrescente).
    # Gli step non-default (es. RAG/MCP) sono pluggabili ma non attivi di default (YAGNI, plan R4).
    original_cascade: tuple[str, ...] = ("requirements", "explicit_original", "provided")

    # Directory canonica dei requisiti (default per l'adapter filesystem).
    requirements_dir: str = "requirements"

    # Prefissi dei bullet EARS estratti da requirements/ (es. **REQ-001**, **FR-002**).
    requirement_id_prefixes: tuple[str, ...] = ("REQ-", "FR-")

    def risk_level(self, severity: str, detectability: str) -> str:
        return _risk(severity, detectability)


DEFAULT_CONFIG = Config()
