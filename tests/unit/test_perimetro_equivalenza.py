"""Presidio anti-divergenza fra le due derivazioni del perimetro (E10-FEAT-060, rischio R-3).

E10-FEAT-060 ALLINEA il comportamento di `ritual_check` a quello di `scan`, ma lo fa **per riuso**,
non per estrazione: `scan._worktree_changes` resta una copia, perche' unificarla significherebbe
toccare il modulo che regge un gate BLOCCANTE su ogni ospite (rinviato a E10-FEAT-066, con
motivazione).

Finche' le copie sono due, la promessa «resteranno allineate» non vale nulla: serve qualcosa che
diventi rosso se una sola delle due viene toccata. E' questo test.

*«Si terra' allineato con la disciplina» non e' una risposta* — Principio XIV.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.scan import _worktree_changes
from sertor_core.wiki_tools.structure import init_structure
from sertor_core.wiki_tools.vcs import worktree_changes

_CONFIG = """\
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"
log_dir = "log"
source_dirs = ["src"]

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _host(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    profile = load_profile(cfg)
    init_structure(profile)
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "-c", "init.defaultBranch=master", "init")
    _git(tmp_path, "config", "user.email", "t@example.test")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "core.autocrlf", "false")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base", "--no-gpg-sign")
    return profile


def test_le_due_derivazioni_vedono_lo_stesso_albero(tmp_path):
    """Stesso albero, stesso insieme di percorsi — o questo test e' rosso.

    Copre le quattro forme che distinguono una derivazione corretta: tracciato modificato, non
    tracciato, cartella nuova con piu' file, file ignorato.
    """
    profile = _host(tmp_path)
    root = profile.config_dir

    (root / "src" / "mod.py").write_text("x = 2\n", encoding="utf-8")        # tracciato modificato
    (root / "src" / "nuovo.py").write_text("y = 1\n", encoding="utf-8")        # non tracciato
    (root / "pacchetto").mkdir()                                               # cartella nuova
    (root / "pacchetto" / "uno.py").write_text("a = 1\n", encoding="utf-8")
    (root / "pacchetto" / "due.py").write_text("b = 2\n", encoding="utf-8")
    (root / ".gitignore").write_text("ignorato.txt\n", encoding="utf-8")
    (root / "ignorato.txt").write_text("shh\n", encoding="utf-8")              # ignorato

    condivisa = worktree_changes(root)
    di_scan = _worktree_changes(profile)

    assert condivisa is not None and di_scan is not None
    assert sorted(condivisa[0]) == sorted(di_scan[0]), "i percorsi cambiati divergono"
    assert sorted(condivisa[1]) == sorted(di_scan[1]), "i percorsi non tracciati divergono"

    # Anti-vacuita': su un albero pulito le due concorderebbero GRATIS, e il test non direbbe nulla.
    assert condivisa[0], "albero inerte: nessun cambiamento da confrontare"
    assert condivisa[1], "albero inerte: nessun file non tracciato da confrontare"
    assert "ignorato.txt" not in condivisa[0]


def test_entrambe_dicono_none_quando_non_possono_guardare(tmp_path):
    """La proprieta' piu' importante da mantenere allineata: nessuna delle due inventa un vuoto."""
    non_repo = tmp_path / "senza_git"
    non_repo.mkdir()
    cfg = non_repo / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    profile = load_profile(cfg)
    init_structure(profile)

    assert worktree_changes(non_repo) is None
    assert _worktree_changes(profile) is None
