"""Stadio 3 — locate_evidence: per ogni FILE aggrega l'evidenza per **simbolo** (G4), non per hunk.

Granularità **ibrida** per-elemento (research R2), **aggregata** (G4): tutti gli hunk di un file che
risolvono lo **stesso simbolo same-file** confluiscono in un unico `EvidenceItem` ancorato a quel simbolo
(righe = lo *span* dei suoi hunk, diff = unione). Così una funzione spaccata da git in più hunk non
genera più item-duplicati. Gli hunk **senza** simbolo same-file ma con contenuto nuovo si accorpano in
**un solo** item-hunk per file. I simboli *cross-layer* (in altri moduli — rischio nº1, research R3)
restano come **contesto** sull'item, senza generare un'àncora a riga propria (la CLI RAG non dà la loro
posizione; un'àncora non verificabile non sopravviverebbe al moat).

Un hunk di sola cancellazione (nessuna riga nuova) non ha nulla da ancorare nel nuovo stato del file →
finisce tra gli `unresolved` (trasparenza, non errore). Le àncore nascono `unverified`: la verifica
(il moat) è lo stadio `verify`.
"""

from __future__ import annotations

from speclift.domain.models import (
    Anchor,
    Changeset,
    EvidenceItem,
    FileChange,
    Hunk,
    Symbol,
)
from speclift.domain.ports import EvidenceLocator


def locate_evidence(
    changeset: Changeset,
    locator: EvidenceLocator,
) -> tuple[list[EvidenceItem], list[Hunk]]:
    items: list[EvidenceItem] = []
    unresolved: list[Hunk] = []

    for file in changeset.files:
        if file.is_binary:
            continue
        file_items, file_unresolved = _locate_file(file, locator)
        items.extend(file_items)
        unresolved.extend(file_unresolved)

    return items, unresolved


def _locate_file(
    file: FileChange, locator: EvidenceLocator
) -> tuple[list[EvidenceItem], list[Hunk]]:
    order: list[str] = []  # simboli nell'ordine di prima apparizione
    by_symbol: dict[str, list[Hunk]] = {}
    symbol_obj: dict[str, Symbol] = {}
    cross_layer: dict[tuple[str, str], Symbol] = {}
    leftover: list[Hunk] = []  # hunk con contenuto nuovo ma senza simbolo same-file
    unresolved: list[Hunk] = []  # cancellazioni → drift

    for hunk in file.hunks:
        symbols = _dedup_symbols(
            locator.locate_symbols(file.path, hunk.candidate_identifiers, _snippet(hunk))
        )
        same_file = [s for s in symbols if s.path == hunk.file_path]
        for s in symbols:
            if s.path != hunk.file_path:
                cross_layer.setdefault((s.name, s.path), s)

        if same_file:
            for s in same_file:
                if s.name not in by_symbol:
                    by_symbol[s.name] = []
                    symbol_obj[s.name] = s
                    order.append(s.name)
                by_symbol[s.name].append(hunk)
        elif _has_new_content(hunk):
            leftover.append(hunk)
        else:
            unresolved.append(hunk)

    cross = list(cross_layer.values())
    items: list[EvidenceItem] = []

    for name in order:
        sym = symbol_obj[name]
        merged = _merge_hunks(by_symbol[name])
        tests = locator.locate_tests(sym)
        anchor = Anchor(
            file=file.path,
            lines=_hunk_lines(merged),
            granularity="symbol",
            status="unverified",
            symbol=name,
            test=tests[0] if tests else None,
        )
        items.append(
            EvidenceItem(
                hunk=merged,
                anchor=anchor,
                granularity_used="symbol",
                symbols=[sym, *cross],
                tests=tests,
            )
        )

    if leftover:
        merged = _merge_hunks(leftover)
        anchor = Anchor(
            file=file.path,
            lines=_hunk_lines(merged),
            granularity="hunk",
            status="unverified",
        )
        items.append(
            EvidenceItem(
                hunk=merged,
                anchor=anchor,
                granularity_used="hunk",
                symbols=list(cross),
            )
        )

    return items, unresolved


def _merge_hunks(hunks: list[Hunk]) -> Hunk:
    """Ricuce più hunk in uno: righe concatenate, range = span, identificatori in unione."""
    if len(hunks) == 1:
        return hunks[0]
    lines: list[str] = []
    ids: dict[str, None] = {}
    for h in hunks:
        lines.extend(h.lines)
        for i in h.candidate_identifiers:
            ids.setdefault(i, None)
    return Hunk(
        file_path=hunks[0].file_path,
        old_range=_range_span([h.old_range for h in hunks]),
        new_range=_range_span([h.new_range for h in hunks]),
        lines=lines,
        candidate_identifiers=list(ids),
    )


def _range_span(ranges: list[tuple[int, int]]) -> tuple[int, int]:
    """Da più (start, len) a un singolo (start, len) che li copre tutti."""
    starts = [start for start, _ in ranges]
    ends = [start + (length - 1 if length > 0 else 0) for start, length in ranges]
    start = min(starts)
    end = max(ends)
    return (start, end - start + 1)


def _hunk_lines(hunk: Hunk) -> tuple[int, int]:
    start, length = hunk.new_range
    return (start, start + length - 1 if length > 0 else start)


def _has_new_content(hunk: Hunk) -> bool:
    return hunk.new_range[1] > 0


def _dedup_symbols(symbols: list[Symbol]) -> list[Symbol]:
    seen: dict[tuple[str, str, int], Symbol] = {}
    for s in symbols:
        seen.setdefault((s.name, s.path, s.line), s)
    return list(seen.values())


def _snippet(hunk: Hunk) -> str:
    added = [ln[1:] for ln in hunk.lines if ln.startswith("+") and not ln.startswith("+++")]
    return "\n".join(added)
