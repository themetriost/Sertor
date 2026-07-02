"""Adapter `OriginalSourceResolver` di default: estrae i requisiti EARS da `requirements/`.

Legge SOLO documenti di requisiti (markdown), MAI codice sorgente (REQ-A01). Estrae i bullet nella
forma `- **REQ-001** …` / `- **FR-002** …` (il formato prodotto dalla fase requirements/speckit),
conservando id, testo e provenienza. Fonte assente/vuota → lista vuota (il chiamante dichiara il gap).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import DEFAULT_CONFIG, Config
from ..domain.models import OriginalRequirement


def _bullet_regex(prefixes: tuple[str, ...]) -> re.Pattern[str]:
    # es. "- **REQ-001**", "- **FR-012**", "- **REQ-A01**"
    # NB: l'alternanza dei prefissi va in un gruppo non-catturante, così il suffisso
    # [A-Za-z0-9]+ si applica a TUTTI i prefissi (non solo all'ultimo).
    alt = "|".join(re.escape(p) for p in prefixes)
    return re.compile(rf"^\s*[-*]\s+\*\*((?:{alt})[A-Za-z0-9]+)\*\*")


def _heading_or_bullet(line: str, bullet_re: re.Pattern[str]) -> bool:
    return line.lstrip().startswith("#") or bool(re.match(r"^\s*[-*]\s+\*\*", line))


def extract_ears_bullets(
    text: str, provenance_prefix: str, prefixes: tuple[str, ...]
) -> list[tuple[str, str]]:
    """Estrae (id, testo) dai bullet EARS. Il testo raccoglie le righe di continuazione del bullet."""

    bullet_re = _bullet_regex(prefixes)
    lines = text.splitlines()
    out: list[tuple[str, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        m = bullet_re.match(lines[i])
        if not m:
            i += 1
            continue
        req_id = m.group(1)
        buf = [lines[i].strip()]
        j = i + 1
        # continuazione: righe non vuote che non aprono un nuovo bullet/heading
        while j < n and lines[j].strip() and not _heading_or_bullet(lines[j], bullet_re):
            buf.append(lines[j].strip())
            j += 1
        out.append((req_id, " ".join(buf)))
        i = j
    return out


class RequirementsFsResolver:
    """Risolve la fonte originale da un path (cartella `requirements/` o singolo documento .md)."""

    def __init__(self, path: str | Path, config: Config = DEFAULT_CONFIG) -> None:
        self._path = Path(path)
        self._config = config

    def _iter_files(self) -> list[Path]:
        if self._path.is_dir():
            return sorted(self._path.rglob("*.md"))
        if self._path.is_file():
            return [self._path]
        return []

    def resolve(self, changeset_ref: str) -> tuple[list[OriginalRequirement], str]:
        files = self._iter_files()
        if not files:
            return [], "absent"

        prefixes = self._config.requirement_id_prefixes
        requirements: list[OriginalRequirement] = []
        idx = 0
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            for req_id, req_text in extract_ears_bullets(text, str(f), prefixes):
                requirements.append(
                    OriginalRequirement(
                        index=idx,
                        id=req_id,
                        text=req_text,
                        provenance=f"{f}",
                    )
                )
                idx += 1

        if not requirements:
            # fonte presente ma vuota di bullet EARS: distinta da 'absent' (FR-003)
            return [], f"present-but-empty:{self._path}"
        return requirements, str(self._path)
