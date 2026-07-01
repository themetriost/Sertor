"""Configurazione centralizzata (Constitution IX).

Tutte le soglie e i percorsi stanno qui: cambiare un valore è una modifica di
configurazione, non un edit sparso nel codice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Cap sul numero di query RAG complementari eseguite per ogni simbolo (multi-search,
#: mitigazione del rischio cross-layer — research R3).
MAX_QUERIES_PER_SYMBOL = 4

#: Soglia (numero di hunk) oltre la quale un changeset è considerato "grande": superato
#: il limite si emette un warning strutturato, non un errore (la pipeline procede).
LARGE_CHANGESET_HUNK_THRESHOLD = 300

#: Versione del contratto EvidenceBundle / SpecLiftReport (deve combaciare con gli schemi).
CONTRACT_VERSION = "1"

#: Suffissi dei file di output.
JSON_OUTPUT_SUFFIX = ".speclift.json"
MD_OUTPUT_SUFFIX = ".speclift.md"

#: Comando-vehicle per invocare il Sertor RAG (mai `import sertor_core`).
SERTOR_RAG_VEHICLE = ("uv", "run", "--project", ".sertor", "sertor-rag")

#: Cartelle di primo livello SEMPRE escluse: specifica e requisiti NON sono fonte di requisiti — sono
#: ciò CONTRO cui SpecLift va confrontato (lavoro di SpecAudit). Includerle sarebbe circolare.
NON_SOURCE_TOP_DIRS = ("specs", "requirements", ".specify")

#: Estensioni considerate DOCUMENTAZIONE: escluse di default, incluse con `--include-docs`
#: (i "due SpecLift": vista codice vs vista codice+doc).
DOC_EXTENSIONS = (".md", ".markdown", ".rst", ".txt", ".adoc")

#: Cartelle di primo livello di sola documentazione (stesso toggle delle doc-extensions).
DOC_TOP_DIRS = ("docs",)


@dataclass(frozen=True)
class Config:
    """Configurazione runtime, letta una volta e iniettata nel composition root."""

    max_queries_per_symbol: int = MAX_QUERIES_PER_SYMBOL
    large_changeset_hunk_threshold: int = LARGE_CHANGESET_HUNK_THRESHOLD
    contract_version: str = CONTRACT_VERSION
    sertor_rag_vehicle: tuple[str, ...] = field(default=SERTOR_RAG_VEHICLE)
    non_source_top_dirs: tuple[str, ...] = field(default=NON_SOURCE_TOP_DIRS)
    doc_extensions: tuple[str, ...] = field(default=DOC_EXTENSIONS)
    doc_top_dirs: tuple[str, ...] = field(default=DOC_TOP_DIRS)


#: Configurazione di default condivisa.
DEFAULT_CONFIG = Config()
