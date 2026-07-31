"""Perimetro di `ritual-check`: unione, dichiarazione, fail-loud (E10-FEAT-060).

La matrice comportamentale che ha diagnosticato il difetto vive QUI, versionata, non in uno
scratchpad: il criterio SC-001 e' un confronto che si puo' MANCARE (righe «consegnato» e «non
consegnato» devono coincidere), non un'affermazione che si puo' sempre dichiarare soddisfatta.

Nota di fixture, pagata una volta: senza un giornale COMMITTATO nel commit di base, `scan` ripiega
su mtime e i suoi numeri sono veri della fixture e falsi del prodotto. Vedi `_git_repo`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.contracts import perimeter_of, scope_of
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.ritual_check import ritual_check
from sertor_core.wiki_tools.structure import init_structure

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

[[taxonomy]]
name = "experiments"
dir = "experiments"
type = "experiment"
"""

_A = "---\ntitle: A\ntype: experiment\ntags: [t]\ncreated: 2026-07-01\nupdated: {u}\n---\n\n{b}\n"
_B = "---\ntitle: B\ntype: experiment\ntags: [t]\ncreated: 2026-07-01\nupdated: {u}\n---\n\n{b}\n"


def _run_git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _page(profile, rel: str, body: str) -> None:
    f = profile.root_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")


def _host(tmp_path: Path):
    """Host git con wiki, un giornale committato e due pagine, poi un ramo di lavoro."""
    tmp_path.mkdir(parents=True, exist_ok=True)  # SC-001 costruisce due host annidati
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    profile = load_profile(cfg)
    init_structure(profile)
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    # Il giornale committato NON e' decorativo: senza, l'ancora ripiega su mtime.
    log_dir = profile.root_path / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "2026-07-01.md").write_text(
        "# Log 2026-07-01\n\n## [2026-07-01] record | base\n\nVoce di base.\n", encoding="utf-8",
    )
    _page(profile, "experiments/a.md", _A.format(u="2026-07-01", b="Testo A."))
    _page(profile, "experiments/b.md", _B.format(u="2026-07-01", b="Testo B."))
    _run_git(tmp_path, "-c", "init.defaultBranch=master", "init")
    _run_git(tmp_path, "config", "user.email", "t@example.test")
    _run_git(tmp_path, "config", "user.name", "Test")
    _run_git(tmp_path, "add", "-A")
    _run_git(tmp_path, "commit", "-m", "base", "--no-gpg-sign")
    _run_git(tmp_path, "checkout", "-b", "work")
    return profile


def _do_the_work(profile) -> None:
    """Lo stesso identico lavoro, usato sia consegnato sia non consegnato."""
    _page(profile, "experiments/a.md",
          _A.format(u="2026-07-30", b="Testo A modificato. [[experiments/b]]"))
    _page(profile, "experiments/b.md",
          _B.format(u="2026-07-30", b="Testo B modificato. [[experiments/a]]"))


# --------------------------------------------------------- SC-001: lo stato VCS non cambia l'esito

def test_sc001_stesso_lavoro_consegnato_o_no_stesso_esito(tmp_path):
    """SC-001 — il perimetro non dipende da `git commit`.

    E' IL criterio della feature, ed e' un confronto che si puo' mancare: prima della riparazione la
    seconda meta' dava `pages=0 distill=0`, la prima `pages=2 distill=1`.
    """
    consegnato = _host(tmp_path / "c")
    _do_the_work(consegnato)
    _run_git(consegnato.config_dir, "add", "-A")
    _run_git(consegnato.config_dir, "commit", "-m", "lavoro", "--no-gpg-sign")
    atteso = ritual_check(consegnato)

    non_consegnato = _host(tmp_path / "n")
    _do_the_work(non_consegnato)
    ottenuto = ritual_check(non_consegnato)

    assert ottenuto.pages_in_scope == atteso.pages_in_scope
    assert len(ottenuto.distill_candidates) == len(atteso.distill_candidates)
    assert [d["signal"] for d in ottenuto.drift_candidates] == \
           [d["signal"] for d in atteso.drift_candidates]
    # Anti-vacuita': se entrambi fossero vuoti l'uguaglianza passerebbe gratis.
    assert atteso.pages_in_scope, "fixture inerte: il caso consegnato non produce pagine in scope"
    assert atteso.distill_candidates, "fixture inerte: nessun candidato da confrontare"


def test_sc002_caso_misto_nessun_candidato_falso(tmp_path):
    """SC-002 — zero segnalazioni false sulla parte non consegnata.

    Prima della riparazione: B veniva segnalata `neighbor-of-change` con «not itself updated», su
    una pagina appena riscritta. Non solo omissione: fabbricazione.
    """
    profile = _host(tmp_path)
    _page(profile, "experiments/a.md",
          _A.format(u="2026-07-30", b="Committato. [[experiments/b]]"))
    _run_git(profile.config_dir, "add", "-A")
    _run_git(profile.config_dir, "commit", "-m", "meta", "--no-gpg-sign")
    _page(profile, "experiments/b.md",
          _B.format(u="2026-07-30", b="NON committato. [[experiments/a]]"))

    res = ritual_check(profile)

    falsi = [d for d in res.drift_candidates
             if d["page"] == "experiments/b.md" and d["signal"] == "neighbor-of-change"]
    assert falsi == [], f"candidato falso su una pagina appena riscritta: {falsi}"
    assert "experiments/b.md" in res.pages_in_scope


def test_pagina_nuova_non_tracciata_entra_in_scope(tmp_path):
    profile = _host(tmp_path)
    _page(profile, "experiments/c.md",
          _A.format(u="2026-07-30", b="Nuova. [[experiments/a]]"))
    res = ritual_check(profile)
    assert "experiments/c.md" in res.pages_in_scope


def test_pagina_distill_nuova_non_tracciata_sopprime_il_candidato(tmp_path):
    """Una pagina di distillazione appena creata e NON consegnata conta come distillazione avvenuta.

    Altrimenti il tool suggerisce di distillare cio' che e' appena stato distillato.
    """
    profile = _host(tmp_path)
    _do_the_work(profile)
    senza = ritual_check(profile)
    assert senza.distill_candidates, "fixture inerte: senza la pagina non c'e' nulla da sopprimere"

    _page(profile, "concepts/entita.md",
          "---\ntitle: E\ntype: concept\ntags: [t]\ncreated: 2026-07-30\n"
          "updated: 2026-07-30\n---\n\nEntita'.\n")
    con = ritual_check(profile)
    assert con.distill_candidates == []


def test_file_ignorato_dal_vcs_non_entra(tmp_path):
    profile = _host(tmp_path)
    (tmp_path / ".gitignore").write_text("wiki/experiments/ignorata.md\n", encoding="utf-8")
    _run_git(tmp_path, "add", ".gitignore")
    _run_git(tmp_path, "commit", "-m", "ignore", "--no-gpg-sign")
    _page(profile, "experiments/ignorata.md", _A.format(u="2026-07-30", b="Invisibile."))
    res = ritual_check(profile)
    assert "experiments/ignorata.md" not in res.pages_in_scope


# ------------------------------------------------------------- dichiarazione del perimetro (US2)

def test_perimetro_dichiarato_sempre_anche_a_zero_candidati(tmp_path):
    """SC-003 — e' il caso in cui serve di piu': uno `0` senza provenienza e' ambiguo."""
    profile = _host(tmp_path)
    res = ritual_check(profile)
    assert res.pages_in_scope == []
    assert res.perimeter["kind"] == "derived"
    nomi = [s["name"] for s in res.perimeter["sources"]]
    assert nomi == ["committed", "worktree"]


def test_perimetro_dichiara_i_conteggi_per_sorgente(tmp_path):
    profile = _host(tmp_path)
    _do_the_work(profile)
    res = ritual_check(profile)
    per_nome = {s["name"]: s["paths"] for s in res.perimeter["sources"]}
    assert per_nome["worktree"] >= 2
    assert per_nome["committed"] == 0
    assert res.scope.endswith("+worktree")


def test_perimetro_esplicito_dichiarato_come_tale(tmp_path):
    profile = _host(tmp_path)
    _do_the_work(profile)
    res = ritual_check(profile, pages=["experiments/a.md"])
    assert res.perimeter["kind"] == "explicit"
    assert res.scope == "explicit:1"


# ------------------------------------------------------------------- contratto derivato (FR-012)

def test_scope_derivata_retrocompatibile_su_solo_committato():
    """Per il perimetro solo-committato la stringa e' IDENTICA a quella emessa prima."""
    p = perimeter_of("derived", [("committed", "abc123...HEAD", 4)])
    assert scope_of(p) == "git:abc123...HEAD"


def test_scope_derivata_dichiara_l_albero_di_lavoro():
    p = perimeter_of("derived", [("committed", "abc123...HEAD", 4), ("worktree", None, 2)])
    assert scope_of(p) == "git:abc123...HEAD+worktree"


def test_scope_esplicita_retrocompatibile():
    assert scope_of(perimeter_of("explicit", [("explicit", None, 3)])) == "explicit:3"


def test_contratto_additivo_i_campi_storici_restano(tmp_path):
    profile = _host(tmp_path)
    data = ritual_check(profile).to_dict()
    for campo in ("scope", "pages_in_scope", "distill_candidates", "drift_candidates",
                  "declaration_scaffold", "schema"):
        assert campo in data
    assert data["schema"] == "wiki.ritual_check/1"


# ----------------------------------------------------------------------- fail-loud (US3, SC-004)

@pytest.mark.parametrize("comando", ["diff-committed", "diff-added", "diff-worktree", "status"])
def test_ogni_interrogazione_del_perimetro_fallisce_forte(tmp_path, monkeypatch, comando):
    """SC-004 — per CIASCUNA interrogazione, un caso che la rende indisponibile.

    Anti-vacuita': il test verifica di aver davvero raggiunto il ramo d'errore (`chiamato`), non
    solo che sia stata sollevata un'eccezione — un `ConfigError` d'altra causa passerebbe gratis.
    """
    profile = _host(tmp_path)
    _do_the_work(profile)

    import sertor_core.wiki_tools.ritual_check as rc
    import sertor_core.wiki_tools.vcs as vcs

    reale_run = vcs.run_git
    chiamato = {"hit": False}

    def _guasta(args, cwd, **kw):
        firma = " ".join(args)
        rotto = (
            (comando == "diff-committed" and firma.startswith("diff --name-only ")
             and "--diff-filter=A" not in firma and "-z" not in firma)
            or (comando == "diff-added" and "--diff-filter=A" in firma)
            or (comando == "diff-worktree" and firma == "diff --name-only -z HEAD")
            or (comando == "status" and firma.startswith("status --porcelain"))
        )
        if rotto:
            chiamato["hit"] = True
            return 128, ""
        return reale_run(args, cwd, **kw)

    monkeypatch.setattr(vcs, "run_git", _guasta)
    monkeypatch.setattr(rc, "run_git", _guasta)

    with pytest.raises(ConfigError):
        ritual_check(profile)
    assert chiamato["hit"], f"il ramo '{comando}' non e' stato raggiunto: il test sarebbe vacuo"


def test_perimetro_indeterminabile_resta_fail_loud(tmp_path):
    """Comportamento odierno da preservare: niente git e niente --pages → errore esplicito."""
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    profile = load_profile(cfg)
    init_structure(profile)
    with pytest.raises(ConfigError):
        ritual_check(profile)
