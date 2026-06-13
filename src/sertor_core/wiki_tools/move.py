"""`move`: sposta una pagina wiki e riscrive i link entranti (FR-001..006, feature 017).

Deterministico/offline (parte D del confine D↔N). Riscrive i wikilink **form-preserving** (le stesse
forme che `lint` riconosce: path POSIX, senza estensione, stem) preservando `|alias`/`#anchor`, e i
link Markdown **relativi** che risolvono alla pagina spostata. Processa le pagine + il file indice;
**non** le partizioni di log (storico append-only). Ordine `rewrite-then-move` con recovery da stato
parziale; collisione (destinazione esistente con sorgente presente) → errore esplicito.
"""
from __future__ import annotations

import logging
import posixpath
import re

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import MoveResult
from sertor_core.wiki_tools.profile import WikiProfile

# Wikilink `[[target(|alias)(#anchor)]]`: gruppo 1 = target, gruppo 2 = suffisso (alias/anchor).
# Coerente con `_WIKILINK` di frontmatter.py (RNF-006: move ↔ lint vedono gli stessi link).
_WIKILINK = re.compile(r"\[\[([^\[\]|#]+)((?:[#|][^\[\]]*)?)\]\]")
# Link Markdown `](path)` (cattura il contenuto tra parentesi).
_MDLINK = re.compile(r"\]\(([^)]+)\)")


def _forms(rel: str) -> dict[str, str]:
    """Le 3 forme di un wikilink verso `rel` (come `lint._link_targets`, ma per categoria)."""
    posix = rel
    no_ext = posix[:-3] if posix.endswith(".md") else posix
    stem = posix.rsplit("/", 1)[-1]
    stem = stem[:-3] if stem.endswith(".md") else stem
    return {"posix": posix, "no_ext": no_ext, "stem": stem}


def _validate_rel(rel: str, label: str) -> str:
    rel = rel.replace("\\", "/").strip()
    if not rel.endswith(".md"):
        raise ConfigError(f"{label} deve essere una pagina .md", key=rel)
    if rel.startswith("/") or ".." in rel.split("/"):
        raise ConfigError(f"{label} deve essere relativo alla radice del wiki", key=rel)
    return rel


def _rewrite(text: str, page_rel: str, src_posix: str, dest_posix: str,
             mapping: dict[str, str]) -> tuple[str, int]:
    """Riscrive wikilink e link relativi che risolvono a `src_posix`. Ritorna (nuovo_testo, n)."""
    occ = 0

    def _wl(m: re.Match) -> str:
        nonlocal occ
        target = m.group(1).strip()
        new = mapping.get(target)
        if new is None:
            return m.group(0)
        occ += 1
        return f"[[{new}{m.group(2)}]]"

    text = _WIKILINK.sub(_wl, text)

    page_dir = posixpath.dirname(page_rel)

    def _md(m: re.Match) -> str:
        nonlocal occ
        raw = m.group(1).strip()
        if "://" in raw or raw.startswith(("#", "/", "<", "mailto:")):
            return m.group(0)
        base, sep, frag = raw.partition("#")
        if not base:
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(page_dir, base)) if page_dir else \
            posixpath.normpath(base)
        if resolved != src_posix:
            return m.group(0)
        occ += 1
        new_rel = posixpath.relpath(dest_posix, page_dir) if page_dir else dest_posix
        return f"]({new_rel}{sep}{frag})"

    text = _MDLINK.sub(_md, text)
    return text, occ


def move(profile: WikiProfile, src: str, dest: str, dry_run: bool = False) -> MoveResult:
    """Sposta `src`→`dest` (relativi alla radice wiki) e riscrive tutti i link entranti.

    Stati (D5): src+!dest = spostamento; src+dest = collisione (errore, REQ-013); !src+dest =
    recovery (completa solo le riscritture, REQ-014); !src+!dest = sorgente non trovata.
    """
    src = _validate_rel(src, "sorgente")
    dest = _validate_rel(dest, "destinazione")
    root = profile.root_path
    src_path = root / src
    dest_path = root / dest
    src_exists = src_path.is_file()
    dest_exists = dest_path.is_file()

    if not src_exists and not dest_exists:
        raise ConfigError("pagina sorgente non trovata", key=src)
    if src_exists and dest_exists and src != dest:
        raise ConfigError("destinazione già esistente (nessuna sovrascrittura)", key=dest)

    old, new = _forms(src), _forms(dest)
    mapping = {old[k]: new[k] for k in ("posix", "no_ext", "stem")}

    # File da scansionare: pagine di contenuto + indice; mai le partizioni di log (D3).
    targets = list(iter_pages(profile))
    if profile.index_path.is_file():
        targets.append((profile.index_file, profile.index_path))

    rewritten: list[dict] = []
    for rel, full in targets:
        try:
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            log_event(logging.WARNING, "move", profile=profile.profile, page=rel,
                      note="unreadable-skip")
            continue
        new_text, occ = _rewrite(text, rel, src, dest, mapping)
        if occ and new_text != text:
            if not dry_run:
                full.write_text(new_text, encoding="utf-8")
            rewritten.append({"page": rel, "occurrences": occ})

    moved = False
    if src_exists and not dest_exists:
        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dest_path)
        moved = True

    log_event(logging.INFO, "move", profile=profile.profile, source=src, destination=dest,
              rewritten=len(rewritten), moved=moved, dry_run=dry_run)
    return MoveResult(source=src, destination=dest, rewritten=rewritten, moved=moved,
                      dry_run=dry_run)
