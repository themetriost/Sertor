"""SpecAudit — auditor di conformità requisito↔codice (MVP).

Confronta due rappresentazioni indipendenti dello stesso requisito — il requisito originale
(forward) e l'output di SpecLift (reverse-engineered, ancorato) — ed emette un verdetto citabile
per requisito, senza mai leggere codice/test/CI.
"""

__version__ = "0.1.0"
