"""L'upgrade deve MUOVERE il runtime, e DIRE dove e' finito (E2, federazione 2026-07-24).

Il difetto che questi test pinnano è stato osservato sul campo da tre nodi indipendenti: tre
upgrade riusciti, e il `sertor-core` del runtime fermo al commit dell'installazione originale
**per un mese**.

Perché nessuno se n'era accorto: `uv add` è idempotente rispetto al **requisito**, e il requisito
che scriviamo è `sertor-core[extras]` — senza vincolo di versione — contro una sorgente git **senza
ref**. Un lock che contiene già il pacchetto soddisfa quel requisito, quindi uv non ha ragione di
ri-risolvere il commit. Il comando girava, il report diceva `UPDATED`, e non si muoveva nulla.

Due proprietà, corrispondenti alle due metà del guasto:
1. su un runtime **esistente** si forza la ri-risoluzione (`uv lock --upgrade-package`);
2. il report dice **cosa risulta adesso**, non «ho eseguito» — è ciò che rende il guasto visibile.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.install_rag import read_runtime_pin

LOCK = """\
version = 1

[[package]]
name = "chromadb"
version = "0.5.0"
source = {{ registry = "https://pypi.org/simple" }}

[[package]]
name = "sertor-core"
version = "{version}"
source = {{ git = "https://github.com/themetriost/Sertor.git#{commit}" }}
dependencies = [
    {{ name = "chromadb" }},
]

[[package]]
name = "shellingham"
version = "1.5.4"
source = {{ registry = "https://pypi.org/simple" }}
"""


def _write_lock(tmp_path: Path, version: str, commit: str) -> Path:
    (tmp_path / "uv.lock").write_text(
        LOCK.format(version=version, commit=commit), encoding="utf-8"
    )
    return tmp_path


# --- leggere l'esito reale ----------------------------------------------------------------------


def test_reads_version_and_commit_from_the_lock(tmp_path):
    """Il lock è la verità: porta il commit risolto, che è ciò che un pin bloccato NON cambia."""
    _write_lock(tmp_path, "0.2.0", "abcdef1234567890")

    assert read_runtime_pin(tmp_path) == ("0.2.0", "abcdef1")


def test_absent_lock_is_unknown_not_a_guess(tmp_path):
    """Nessun lock ⇒ `None`. Il chiamante dirà «UNKNOWN», non inventerà una versione."""
    assert read_runtime_pin(tmp_path) is None


def test_lock_without_sertor_core_is_unknown(tmp_path):
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "chromadb"\nversion = "0.5.0"\n', encoding="utf-8"
    )

    assert read_runtime_pin(tmp_path) is None


def test_unreadable_lock_does_not_raise(tmp_path):
    """Un lock illeggibile non deve far fallire l'upgrade: degrada a «sconosciuto»."""
    (tmp_path / "uv.lock").mkdir()  # una directory al posto del file

    assert read_runtime_pin(tmp_path) is None


def test_a_moved_pin_is_visible(tmp_path):
    """La proprietà che serve davvero: due letture diverse ⇒ il runtime si è mosso.

    Con la sola informazione «il comando è stato eseguito» questa distinzione è impossibile, ed è
    esattamente per questo che tre upgrade a vuoto sono passati per riusciti.
    """
    before = read_runtime_pin(_write_lock(tmp_path, "0.1.0", "cbcbae2000000000"))
    after = read_runtime_pin(_write_lock(tmp_path, "0.2.0", "5aed197000000000"))

    assert before != after
    assert before == ("0.1.0", "cbcbae2")
    assert after == ("0.2.0", "5aed197")


def test_a_stuck_pin_is_visible_too(tmp_path):
    """Il caso che si vuole poter NOMINARE: dopo l'upgrade il runtime è dov'era."""
    before = read_runtime_pin(_write_lock(tmp_path, "0.1.0", "cbcbae2000000000"))
    after = read_runtime_pin(_write_lock(tmp_path, "0.1.0", "cbcbae2000000000"))

    assert before == after, "invariato: il report deve dirlo, non implicare movimento"


# --- forzare la ri-risoluzione ------------------------------------------------------------------


class FakeRunner:
    """Registra i comandi eseguiti; `uv` sempre disponibile."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def is_available(self, name: str) -> bool:
        return True

    def run(self, cmd, cwd=None):
        self.commands.append(list(cmd))
        return type("Res", (), {"ok": True, "stderr": "", "returncode": 0})()


@pytest.fixture
def profile(tmp_path):
    from sertor_installer.rag_profile import RagHostProfile

    return RagHostProfile(
        target_root=tmp_path, backend="local", corpus="demo",
        extras=("mcp",),
    )


def test_existing_runtime_forces_the_re_resolution(profile, tmp_path):
    """Su un runtime già presente NON basta `uv add`: serve chiedere a uv di ri-risolvere."""
    from sertor_installer.install_rag import _apply_deps

    sertor_dir = profile.sertor_dir
    sertor_dir.mkdir(parents=True, exist_ok=True)
    (sertor_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    runner = FakeRunner()

    _apply_deps(profile, runner)

    joined = [" ".join(c) for c in runner.commands]
    assert any("lock --upgrade-package sertor-core" in c for c in joined), (
        "senza questo il pin non si muove: e' il difetto osservato sul campo"
    )
    assert any(c.endswith("sync") for c in joined), "dopo il re-lock serve il sync"


def test_fresh_runtime_does_not_need_the_force(profile):
    """Su un'installazione nuova `uv add` risolve gia' fresco: nessun re-lock superfluo."""
    from sertor_installer.install_rag import _apply_deps

    runner = FakeRunner()

    _apply_deps(profile, runner)

    joined = [" ".join(c) for c in runner.commands]
    assert not any("--upgrade-package" in c for c in joined)


def test_report_names_the_resulting_version_not_the_command(profile):
    """Il report deve dire COSA RISULTA, non «ho eseguito un comando» (Fail Loud sull'installer)."""
    from sertor_installer.install_rag import _apply_deps

    sertor_dir = profile.sertor_dir
    sertor_dir.mkdir(parents=True, exist_ok=True)
    _write_lock(sertor_dir, "0.2.0", "5aed197000000000")
    runner = FakeRunner()

    outcome = _apply_deps(profile, runner)

    assert "0.2.0" in outcome.detail
    assert "5aed197" in outcome.detail
    assert "uv add" not in outcome.detail, "il comando eseguito non e' l'esito"


def test_report_says_unknown_when_the_lock_cannot_be_read(profile):
    """Se l'esito non e' verificabile lo si DICE, invece di lasciar credere che sia andato bene."""
    from sertor_installer.install_rag import _apply_deps

    runner = FakeRunner()

    outcome = _apply_deps(profile, runner)

    assert "UNKNOWN" in outcome.detail
