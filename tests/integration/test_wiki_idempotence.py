"""Test US4 — idempotenza strutturale delle operazioni del wiki (REQ-050, SC-002)."""
from __future__ import annotations

import hashlib

from sertor_core.wiki.conventions import Brief
from sertor_core.wiki.operations import record
from sertor_core.wiki.structure import create_wiki

T = "2026-06-03"


def _digest(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.md")):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def test_double_create_is_identical(tmp_path):
    root = tmp_path / "wiki"
    create_wiki(root, today=T)
    d1 = _digest(root)
    create_wiki(root, today="2026-07-01")        # re-run (anche con data diversa)
    assert _digest(root) == d1                     # file identici (SC-002)


def test_double_record_is_identical(wiki_sandbox):
    record(wiki_sandbox, Brief("Tema", "concept", "corpo stabile"), today=T)
    d1 = _digest(wiki_sandbox)
    record(wiki_sandbox, Brief("Tema", "concept", "corpo stabile"), today="2026-07-01")
    assert _digest(wiki_sandbox) == d1             # nessun timestamp/voce modificati (REQ-050)


def test_changed_body_updates_only_then(wiki_sandbox):
    record(wiki_sandbox, Brief("Tema", "concept", "v1"), today=T)
    d1 = _digest(wiki_sandbox)
    res = record(wiki_sandbox, Brief("Tema", "concept", "v2 modificata"), today="2026-07-01")
    assert res.changed is True                      # contenuto cambiato → scrive
    assert _digest(wiki_sandbox) != d1
