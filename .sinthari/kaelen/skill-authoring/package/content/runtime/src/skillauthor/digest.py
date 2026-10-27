"""Impronta di una cartella-skill: lega un verdetto alla versione della skill che è stata collaudata.

sha256 su ogni file (percorso relativo + contenuto), in ordine, ignorando `__pycache__`. Una modifica
qualunque dopo il collaudo cambia l'impronta, e il gate lo vede.

I fine riga non contano: nei file di testo CRLF e CR diventano LF prima dell'impronta. Su Windows uno
strumento che scrive in CRLF dava a una skill un'impronta diversa da quella che avrebbe avuto dopo il commit
(git normalizza in LF), e il gate rispondeva `verdict-stale` su una skill invariata. Sui file già in LF
l'impronta resta quella di prima. Un file con un byte NUL è binario e conta byte per byte.

Un agente è un file solo (feature 006, R2): la sua impronta è quella del contenuto normalizzato, senza il
nome del file, così una copia installata altrove ha l'impronta della sorgente. Su un file non c'è
ordinamento, quindi l'impronta di un agente non dipende dal sistema operativo, a differenza di quella di
una cartella.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .config import PARITY_IGNORE


def skill_digest(skill_dir: Path) -> str:
    h = hashlib.sha256()
    files = sorted(
        p
        for p in skill_dir.rglob("*")
        if p.is_file() and not any(part in PARITY_IGNORE for part in p.relative_to(skill_dir).parts)
    )
    for path in files:
        h.update(path.relative_to(skill_dir).as_posix().encode("utf-8") + b"\0")
        h.update(_normalised(path.read_bytes()) + b"\0")
    return f"sha256:{h.hexdigest()}"


def agent_digest(agent_file: Path) -> str:
    return f"sha256:{hashlib.sha256(_normalised(agent_file.read_bytes())).hexdigest()}"


def _normalised(data: bytes) -> bytes:
    if b"\0" in data:
        return data
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
