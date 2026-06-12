"""Merge additivo del `.sertor/.env` (FR-014/015/016, M1).

Assente → crea dal template (segreti vuoti). Presente → aggiunge SOLO le chiavi mancanti, **mai**
sovrascrive il valore di una chiave esistente (REQ-222). Eccezione mirata (M1): per
`SERTOR_EXCLUDE_PATTERNS` garantisce comunque la presenza di `.sertor` (lo appende al valore
esistente se manca), perché l'esclusione del runtime dall'indicizzazione è una correttezza, non una
preferenza utente. Nessun segreto viene mai scritto con valore (i template li lasciano vuoti).
"""
from __future__ import annotations

from pathlib import Path

from sertor_installer.artifacts import Outcome

_EXCLUDE_KEY = "SERTOR_EXCLUDE_PATTERNS"
_SERTOR_DIR = ".sertor"


def _parse_pairs(text: str) -> dict[str, str]:
    """Estrae `KEY=value` (ignora commenti/righe vuote). Ultima vince (semantica dotenv)."""
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        pairs[k.strip()] = v.strip()
    return pairs


def _replace_key_line(text: str, key: str, new_line: str) -> str:
    """Sostituisce la riga `key=...` con `new_line`, preservando il resto."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and s.split("=", 1)[0].strip() == key:
            out.append(new_line)
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def merge_env(env_path: Path, rendered: str) -> tuple[Outcome, str]:
    """Applica il merge additivo. `rendered` = template già compilato (corpus iniettato)."""
    template = _parse_pairs(rendered)

    if not env_path.exists():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(
            rendered if rendered.endswith("\n") else rendered + "\n", encoding="utf-8"
        )
        return Outcome.CREATED, f"{len(template)} chiavi"

    existing_text = env_path.read_text(encoding="utf-8")
    existing = _parse_pairs(existing_text)
    new_text = existing_text
    added: list[str] = []
    ensured_sertor = False

    # M1: garantisci `.sertor` negli excludes anche se la chiave esiste già.
    if _EXCLUDE_KEY in existing:
        items = [p.strip() for p in existing[_EXCLUDE_KEY].split(",") if p.strip()]
        if _SERTOR_DIR not in items:
            items.append(_SERTOR_DIR)
            new_text = _replace_key_line(
                new_text, _EXCLUDE_KEY, f"{_EXCLUDE_KEY}={','.join(items)}"
            )
            ensured_sertor = True

    # Chiavi mancanti: append (mai sovrascrivere valori esistenti).
    missing = [f"{k}={v}" for k, v in template.items() if k not in existing]
    if missing:
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += "\n".join(missing) + "\n"
        added = [line.split("=", 1)[0] for line in missing]

    if not missing and not ensured_sertor:
        return Outcome.SKIPPED, "già presente"

    env_path.write_text(new_text, encoding="utf-8")
    parts: list[str] = []
    if added:
        parts.append(f"+{len(added)} chiavi")
    if ensured_sertor:
        parts.append(".sertor aggiunto agli excludes")
    return Outcome.MERGED, "; ".join(parts)
