"""`vcs.worktree_changes`: la derivazione condivisa del lavoro non consegnato (E10-FEAT-060).

Vive in `vcs.py` perche' DUE capacita' ne hanno bisogno — il gate bloccante e la scoperta per-step —
e finche' ognuna se la derivava per conto proprio misuravano realta' diverse senza che nulla le
confrontasse. Qui si fissano le proprieta' che rendono quella derivazione corretta.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from sertor_core.wiki_tools.vcs import split_z, worktree_changes


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "-c", "init.defaultBranch=master", "init")
    _git(tmp_path, "config", "user.email", "t@example.test")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "core.autocrlf", "false")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base", "--no-gpg-sign")
    return tmp_path


def test_file_tracciato_modificato_compare(tmp_path):
    repo = _repo(tmp_path)
    (repo / "src" / "mod.py").write_text("x = 2\n", encoding="utf-8")
    changed, untracked = worktree_changes(repo)
    assert "src/mod.py" in changed
    assert untracked == []


def test_file_non_tracciato_compare_ed_e_marcato_come_tale(tmp_path):
    repo = _repo(tmp_path)
    (repo / "src" / "nuovo.py").write_text("y = 1\n", encoding="utf-8")
    changed, untracked = worktree_changes(repo)
    assert "src/nuovo.py" in changed
    assert untracked == ["src/nuovo.py"]


def test_cartella_nuova_nomina_i_file_non_la_cartella(tmp_path):
    """`-uall`: per default git collassa una cartella non tracciata in un'unica voce.

    Nominare `pacchetto/` dove il punto e' sapere QUALI file la compongono renderebbe la
    dichiarazione inutilizzabile.
    """
    repo = _repo(tmp_path)
    (repo / "pacchetto").mkdir()
    (repo / "pacchetto" / "uno.py").write_text("a = 1\n", encoding="utf-8")
    (repo / "pacchetto" / "due.py").write_text("b = 2\n", encoding="utf-8")
    _, untracked = worktree_changes(repo)
    assert sorted(untracked) == ["pacchetto/due.py", "pacchetto/uno.py"]
    assert "pacchetto/" not in untracked


def test_rinomina_contata_una_volta_sulla_destinazione(tmp_path):
    repo = _repo(tmp_path)
    _git(repo, "mv", "src/mod.py", "src/rinominato.py")
    changed, _ = worktree_changes(repo)
    assert changed.count("src/rinominato.py") <= 1
    assert "src/mod.py" not in changed


def test_file_ignorato_non_entra_mai(tmp_path):
    repo = _repo(tmp_path)
    (repo / ".gitignore").write_text("segreti.txt\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore", "--no-gpg-sign")
    (repo / "segreti.txt").write_text("shh\n", encoding="utf-8")
    changed, untracked = worktree_changes(repo)
    assert "segreti.txt" not in changed
    assert "segreti.txt" not in untracked


def test_sole_terminazioni_di_riga_non_entrano(tmp_path):
    """Content-aware: un file «toccato» dove nessuno ha scritto nulla non e' lavoro.

    Contarlo bloccherebbe una sessione per un file che nessuno ha modificato — occorso davvero alla
    prima applicazione reale del gate.
    """
    repo = _repo(tmp_path)
    (repo / "src" / "mod.py").write_bytes(b"x = 1\r\n")  # stesso contenuto, altre terminazioni
    changed, _ = worktree_changes(repo)
    assert "src/mod.py" not in changed


def test_git_indisponibile_ritorna_none_non_lista_vuota(tmp_path):
    """`None`, mai `([], [])`: un insieme vuoto si legge «non c'e' nulla da fare».

    La funzione non deve poterlo dire quando non e' riuscita a guardare.
    """
    non_repo = tmp_path / "senza_git"
    non_repo.mkdir()
    assert worktree_changes(non_repo) is None


def test_split_z_scarta_i_token_vuoti():
    assert split_z("a\0b\0") == ["a", "b"]
    assert split_z("") == []
