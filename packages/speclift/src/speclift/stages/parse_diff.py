"""Stadio 2 — parse_diff: testo unified-diff → `Changeset` (file/hunk/identificatori).

Funzione pura, testabile su testo senza `git`. Salta il contenuto dei file binari, riconosce
add/delete/rename, e per ogni hunk estrae identificatori candidati (utili al retrieval RAG a valle).
"""

from __future__ import annotations

import re

from speclift.domain.models import Changeset, FileChange, Hunk, RawDiff

_DIFF_GIT = re.compile(r"^diff --git ")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
_RENAME_FROM = re.compile(r"^rename from (.+)$")
_RENAME_TO = re.compile(r"^rename to (.+)$")
_MINUS = re.compile(r"^--- (?:a/)?(.+)$")
_PLUS = re.compile(r"^\+\+\+ (?:b/)?(.+)$")

# Dichiarazioni con nome: def/class/func/function/fn/struct/enum/trait/type/const NAME.
# (G6) Esclusi `let`/`var`: introducono variabili LOCALI, non simboli da ancorare → rumore col RAG.
_DECL = re.compile(r"\b(?:def|class|func|function|fn|struct|enum|trait|type|const)\s+([A-Za-z_]\w*)")
# (G6) Solo assegnazioni a LIVELLO MODULO (colonna 0): costanti/simboli top-level. Le assegnazioni
# indentate sono variabili locali (rumore). `(?!=)` evita di matchare i confronti `==`.
_ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*[:=](?!=)")


def parse_diff(raw: RawDiff) -> Changeset:
    files: list[FileChange] = []
    builder: _FileBuilder | None = None

    for line in raw.text.splitlines():
        if _DIFF_GIT.match(line):
            if builder is not None:
                files.append(builder.build())
            builder = _FileBuilder()
            continue
        if builder is None:
            continue
        builder.feed(line)

    if builder is not None:
        files.append(builder.build())

    return Changeset(ref=raw.ref, kind=raw.kind, files=files)


class _FileBuilder:
    """Accumula lo stato di un singolo blocco `diff --git` e ne produce un `FileChange`."""

    def __init__(self) -> None:
        self.path: str | None = None
        self.old_path: str | None = None
        self.is_binary = False
        self.is_new = False
        self.is_deleted = False
        self.is_rename = False
        self.hunks: list[Hunk] = []
        self._cur: _HunkBuilder | None = None

    def feed(self, line: str) -> None:
        if line.startswith("new file mode"):
            self.is_new = True
            return
        if line.startswith("deleted file mode"):
            self.is_deleted = True
            return
        if line.startswith("Binary files") or line.startswith("GIT binary patch"):
            self.is_binary = True
            return

        m = _RENAME_FROM.match(line)
        if m:
            self.is_rename = True
            self.old_path = m.group(1).strip()
            return
        m = _RENAME_TO.match(line)
        if m:
            self.is_rename = True
            self.path = m.group(1).strip()
            return

        m = _MINUS.match(line)
        if m:
            old = m.group(1).strip()
            if old != "/dev/null" and self.old_path is None:
                self.old_path = old
            return
        m = _PLUS.match(line)
        if m:
            new = m.group(1).strip()
            if new != "/dev/null":
                self.path = new
            return

        m = _HUNK.match(line)
        if m:
            self._close_hunk()
            old_start, old_len, new_start, new_len, header_ctx = m.groups()
            self._cur = _HunkBuilder(
                file_path=self.path or self.old_path or "",
                old_range=(int(old_start), int(old_len) if old_len else 1),
                new_range=(int(new_start), int(new_len) if new_len else 1),
            )
            self._cur.feed_header_context(header_ctx)
            return

        if self._cur is not None and line[:1] in (" ", "+", "-"):
            self._cur.feed_body(line)

    def _close_hunk(self) -> None:
        if self._cur is not None:
            self.hunks.append(self._cur.build())
            self._cur = None

    def build(self) -> FileChange:
        self._close_hunk()
        if self.is_rename:
            change_type = "renamed"
        elif self.is_new:
            change_type = "added"
        elif self.is_deleted:
            change_type = "deleted"
        else:
            change_type = "modified"
        return FileChange(
            path=self.path or self.old_path or "",
            change_type=change_type,
            old_path=self.old_path if self.is_rename else None,
            is_binary=self.is_binary,
            hunks=[] if self.is_binary else self.hunks,
        )


class _HunkBuilder:
    def __init__(
        self,
        file_path: str,
        old_range: tuple[int, int],
        new_range: tuple[int, int],
    ) -> None:
        self.file_path = file_path
        self.old_range = old_range
        self.new_range = new_range
        self.lines: list[str] = []
        self._ids: list[str] = []

    def feed_header_context(self, ctx: str) -> None:
        # L'header "@@ ... @@ <ctx>" porta spesso la firma del simbolo che racchiude l'hunk.
        self._collect_ids(ctx)

    def feed_body(self, line: str) -> None:
        self.lines.append(line)
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            self._collect_ids(line[1:])

    def _collect_ids(self, text: str) -> None:
        for m in _DECL.finditer(text):
            self._ids.append(m.group(1))
        am = _ASSIGN.match(text)
        if am:
            self._ids.append(am.group(1))

    def build(self) -> Hunk:
        seen: dict[str, None] = {}
        for i in self._ids:
            seen.setdefault(i, None)
        return Hunk(
            file_path=self.file_path,
            old_range=self.old_range,
            new_range=self.new_range,
            lines=list(self.lines),
            candidate_identifiers=list(seen),
        )
