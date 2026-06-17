"""Verifica di packaging ripetibile — contratto ``packaging.verify/1`` (FEAT-001 epica sertor-cli).

Implementa la suite di verifica della feature *packaging distribuibile* (`specs/047-packaging-
distribuibile/contracts/packaging-verification.md`). Quattro stage a costo crescente:

1. **Coerenza statica** (no build, offline-totale): licenza presente+coerente, versione allineata a
   `/VERSION`, `requires-python >= 3.11`, metadati user-facing.
2. **Build dell'artefatto** (`uv build`, offline rispetto a PyPI): sdist+wheel, `LICENSE` in wheel,
   `assets/**` per `sertor`, entry-point dichiarati, METADATA user-facing.
3. **Install pulito a un comando** in venv effimero: `uv`/`uvx` (gate) e `pip` (best-effort, xfail).
4. **Invarianti preservati**: install≠run, nessun segreto, isolamento in `tmp_path`, host-agnostico.

Vincoli architetturali (dal contratto):
- **NESSUN import di `sertor_core`** (Principio XI): esercita gli artefatti, non la libreria.
- Ispezione = **stdlib pura** (`tomllib`, `zipfile`, `email.parser`, `configparser`).
- Build/install = **subprocess** verso `uv`/`pip` — mai import diretti.
- Precondizione assente (`uv`/GitHub) → `pytest.skip` esplicito azionabile, mai falso verde.
- Nessun segreto/credenziale in questo file.
"""
from __future__ import annotations

import configparser
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# --- Topologia del workspace (relativa a questo file, host-agnostica) -----------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = REPO_ROOT / "VERSION"
REPO_URL = "https://github.com/themetriost/Sertor"

# (nome pacchetto, dir del pyproject relativa alla root, kind, subdirectory per git+url)
#   kind: "user-facing" (install diretto, metadati completi) | "internal" (dipendenza, esonerata)
PACKAGES = {
    "sertor-core": {"dir": REPO_ROOT, "kind": "internal", "subdir": "."},
    "sertor": {"dir": REPO_ROOT / "packages" / "sertor", "kind": "user-facing",
               "subdir": "packages/sertor"},
    "sertor-flow": {"dir": REPO_ROOT / "packages" / "sertor-flow", "kind": "user-facing",
                    "subdir": "packages/sertor-flow"},
    "sertor-install-kit": {"dir": REPO_ROOT / "packages" / "sertor-install-kit", "kind": "internal",
                           "subdir": "packages/sertor-install-kit"},
}
USER_FACING = [n for n, m in PACKAGES.items() if m["kind"] == "user-facing"]

# Entry-point console-script attesi per pacchetto (REQ-023).
EXPECTED_SCRIPTS = {
    "sertor": {"sertor"},
    "sertor-flow": {"sertor-flow"},
    "sertor-core": {"sertor-rag", "sertor-wiki-tools"},
    "sertor-install-kit": set(),
}

# Pattern grossolani di segreti che non devono mai comparire nei file versionati/artefatti (SC-009).
SECRET_HINTS = ("AZURE_OPENAI_API_KEY", "AZURE_SEARCH_API_KEY", "sk-", "AKIA", "-----BEGIN ")


# --- Helper stdlib (nessun import di sertor_core) -------------------------------------------------

def _read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def _license_path(pkg: str) -> Path:
    """Percorso del LICENSE del pacchetto (la root È sertor-core)."""
    if pkg == "sertor-core":
        return REPO_ROOT / "LICENSE"
    return PACKAGES[pkg]["dir"] / "LICENSE"


def _load_pyproject(pkg: str) -> dict:
    path = PACKAGES[pkg]["dir"] / "pyproject.toml"
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _project_table(pkg: str) -> dict:
    return _load_pyproject(pkg).get("project", {})


def _resolved_version(pkg: str) -> str:
    """Versione effettiva del pacchetto: statica se presente, altrimenti dinamica da VERSION."""
    project = _project_table(pkg)
    if "version" in project:
        return project["version"]
    # dynamic = ["version"] → letta da [tool.hatch.version] path = .../VERSION
    hatch_version = _load_pyproject(pkg).get("tool", {}).get("hatch", {}).get("version", {})
    rel = hatch_version.get("path")
    assert rel, f"{pkg}: né version statico né [tool.hatch.version].path"
    version_path = (PACKAGES[pkg]["dir"] / rel).resolve()
    return version_path.read_text(encoding="utf-8").strip()


def _license_text_is_mit(text: str) -> bool:
    head = text.lstrip().splitlines()[0].strip().upper() if text.strip() else ""
    return head.startswith("MIT LICENSE") and "WITHOUT WARRANTY OF ANY KIND" in text.upper()


def _license_spdx(pkg: str) -> str | None:
    """Espressione SPDX della licenza, sia forma PEP 639 (str) sia legacy `{ text = ... }`."""
    lic = _project_table(pkg).get("license")
    if isinstance(lic, str):
        return lic
    if isinstance(lic, dict):
        return lic.get("text")
    return None


def _uv_available() -> bool:
    return shutil.which("uv") is not None


def _wheel_for(pkg: str, dist_dir: Path) -> Path | None:
    # Il nome del file normalizza '-' in '_' (sertor-core -> sertor_core).
    stem = pkg.replace("-", "_")
    matches = sorted(dist_dir.glob(f"{stem}-*.whl"))
    return matches[0] if matches else None


def _sdist_for(pkg: str, dist_dir: Path) -> Path | None:
    stem = pkg.replace("-", "_")
    matches = sorted(dist_dir.glob(f"{stem}-*.tar.gz"))
    return matches[0] if matches else None


def _wheel_names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as zf:
        return zf.namelist()


def _wheel_metadata(wheel: Path) -> dict[str, list[str]]:
    """Parsa il METADATA RFC822 della wheel → mapping header → lista valori (multi-valore)."""
    with zipfile.ZipFile(wheel) as zf:
        meta_name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        raw = zf.read(meta_name).decode("utf-8")
    msg = Parser().parsestr(raw)
    out: dict[str, list[str]] = {}
    for key in msg.keys():
        out.setdefault(key, [])
    for key, value in msg.items():
        out.setdefault(key, []).append(value)
    return out


def _wheel_entry_points(wheel: Path) -> set[str]:
    with zipfile.ZipFile(wheel) as zf:
        ep_files = [n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")]
        if not ep_files:
            return set()
        raw = zf.read(ep_files[0]).decode("utf-8")
    parser = configparser.ConfigParser()
    parser.read_string(raw)
    if not parser.has_section("console_scripts"):
        return set()
    return set(parser.options("console_scripts"))


# --- Fixture: build di tutti i pacchetti una sola volta (Stage 2) ---------------------------------

@pytest.fixture(scope="session")
def built_dist(tmp_path_factory) -> Path:
    """Builda i 4 pacchetti in una dir temporanea condivisa (Stage 2). Skip se `uv` assente.

    `uv build` non contatta PyPI (build da sorgente locale). Opera su `tmp_path`, non tocca il repo.
    """
    if not _uv_available():
        pytest.skip("uv non in PATH — Stage 2/3 non eseguibili")
    dist_dir = tmp_path_factory.mktemp("packaging_dist")
    for pkg in PACKAGES:
        proc = subprocess.run(
            ["uv", "build", "--package", pkg, "--out-dir", str(dist_dir)],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        # C2.2 — su build failure il referto identifica package + stage.
        assert proc.returncode == 0, (
            f"stage=build package={pkg}: uv build fallito (exit {proc.returncode})\n{proc.stderr}"
        )
    return dist_dir


# =================================================================================================
# Stage 1 — Coerenza statica di metadati e licenza (no build, offline-totale)
# =================================================================================================

def test_license_files_present():
    """C1.1 — LICENSE in radice e in ogni package dir (FR-001, SC-001)."""
    assert (REPO_ROOT / "LICENSE").is_file(), "stage=license: manca /LICENSE in radice"
    for pkg, meta in PACKAGES.items():
        if pkg == "sertor-core":
            continue  # la root È sertor-core: il LICENSE di radice è il suo
        assert (meta["dir"] / "LICENSE").is_file(), (
            f"stage=license package={pkg}: manca {meta['dir'] / 'LICENSE'}"
        )


def test_license_coherent():
    """C1.2 — `[project].license` == MIT in ogni pkg e il LICENSE è testo MIT (FR-002)."""
    for pkg in PACKAGES:
        spdx = _license_spdx(pkg)
        assert spdx == "MIT", f"stage=license package={pkg}: license = {spdx!r}, atteso 'MIT'"
    root_license = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert _license_text_is_mit(root_license), "stage=license: il testo /LICENSE non è MIT"
    for pkg in PACKAGES:
        text = _license_path(pkg).read_text(encoding="utf-8")
        assert _license_text_is_mit(text), f"stage=license package={pkg}: LICENSE non è testo MIT"


def test_license_without_text_fails():
    """C1.3 — se un pkg dichiara license=MIT ma manca il file LICENSE → incoerenza (FR-004).

    Verifica l'invariante: ogni pkg che dichiara MIT HA il file. (Non esiste il caso opposto.)
    """
    for pkg in PACKAGES:
        if _license_spdx(pkg) != "MIT":
            continue
        license_path = _license_path(pkg)
        assert license_path.is_file(), (
            f"stage=license package={pkg}: dichiara MIT ma manca il file {license_path}"
        )


def test_versions_aligned():
    """C1.4 — la versione risolta dei 4 pyproject == contenuto di /VERSION (FR-011, SC-007)."""
    expected = _read_version()
    assert expected, "stage=metadata: /VERSION è vuoto"
    for pkg in PACKAGES:
        resolved = _resolved_version(pkg)
        assert resolved == expected, (
            f"stage=metadata package={pkg}: versione {resolved!r} != /VERSION {expected!r}"
        )


def test_requires_python():
    """C1.5 — ogni pkg dichiara `requires-python >= 3.11` (FR-012)."""
    for pkg in PACKAGES:
        rp = _project_table(pkg).get("requires-python", "")
        assert ">=3.11" in rp.replace(" ", ""), (
            f"stage=metadata package={pkg}: requires-python = {rp!r}, atteso '>=3.11'"
        )


def test_user_facing_metadata():
    """C1.6/C1.7 — user-facing: name/version/description/authors/license + urls.Repository."""
    expected_version = _read_version()
    for pkg in USER_FACING:
        project = _project_table(pkg)
        assert project.get("name") == pkg, f"stage=metadata package={pkg}: name errato"
        assert _resolved_version(pkg) == expected_version, (
            f"stage=metadata package={pkg}: versione disallineata"
        )
        assert project.get("description"), f"stage=metadata package={pkg}: description mancante"
        assert project.get("authors"), f"stage=metadata package={pkg}: authors mancante"
        assert _license_spdx(pkg) == "MIT", f"stage=metadata package={pkg}: license mancante/errata"
        urls = project.get("urls", {})
        assert urls.get("Repository"), f"stage=metadata package={pkg}: urls.Repository mancante"


def test_classifiers_keywords():
    """C1.8 (Should) — user-facing dichiarano classifiers + keywords (FR-013)."""
    for pkg in USER_FACING:
        project = _project_table(pkg)
        assert project.get("classifiers"), f"stage=metadata package={pkg}: classifiers mancanti"
        assert project.get("keywords"), f"stage=metadata package={pkg}: keywords mancanti"


def test_internal_packages_exempt_from_user_facing_metadata():
    """DA-P4 — i pacchetti interni sono esonerati dai metadati user-facing (build-validati).

    `sertor-install-kit` non ha gate su urls/classifiers; solo la licenza resta obbligatoria.
    """
    internal = [n for n, m in PACKAGES.items() if m["kind"] == "internal"]
    assert internal, "atteso almeno un pacchetto interno"
    for pkg in internal:
        assert _license_spdx(pkg) == "MIT", f"stage=license package={pkg}: anche gli interni MIT"


# =================================================================================================
# Stage 2 — Build dell'artefatto (uv build, offline rispetto a PyPI)
# =================================================================================================

def test_build_produces_artifacts(built_dist):
    """C2.1 — per ogni pkg, uv build produce sia sdist sia wheel senza errori (FR-020, SC-003)."""
    for pkg in PACKAGES:
        sdist = _sdist_for(pkg, built_dist)
        wheel = _wheel_for(pkg, built_dist)
        assert sdist and sdist.is_file(), f"stage=build package={pkg}: sdist non prodotto"
        assert wheel and wheel.is_file(), f"stage=build package={pkg}: wheel non prodotta"


def test_license_in_wheel(built_dist):
    """C2.3 — la wheel di ogni pkg contiene un file LICENSE (FR-003, SC-001)."""
    for pkg in PACKAGES:
        wheel = _wheel_for(pkg, built_dist)
        assert wheel, f"stage=wheel-contents package={pkg}: wheel mancante"
        names = _wheel_names(wheel)
        has_license = any(Path(n).name == "LICENSE" for n in names)
        assert has_license, f"stage=wheel-contents package={pkg}: LICENSE non incluso nella wheel"


def test_assets_in_sertor_wheel(built_dist):
    """C2.4 — la wheel di `sertor` contiene `assets/**` (package-data, FR-021)."""
    wheel = _wheel_for("sertor", built_dist)
    assert wheel, "stage=wheel-contents package=sertor: wheel mancante"
    names = _wheel_names(wheel)
    asset_entries = [n for n in names if "/assets/" in n and not n.endswith("/")]
    assert asset_entries, "stage=wheel-contents package=sertor: assets/** assenti nella wheel"


def test_entry_points_declared(built_dist):
    """C2.5 — la wheel dichiara i console-script attesi (FR-023)."""
    for pkg, expected in EXPECTED_SCRIPTS.items():
        wheel = _wheel_for(pkg, built_dist)
        assert wheel, f"stage=entry-points package={pkg}: wheel mancante"
        scripts = _wheel_entry_points(wheel)
        assert scripts == expected, (
            f"stage=entry-points package={pkg}: console-script {scripts}, atteso {expected}"
        )


def test_user_facing_wheel_metadata(built_dist):
    """C2.6 — METADATA delle wheel user-facing: licenza, Project-URL e (Should) classifiers."""
    for pkg in USER_FACING:
        wheel = _wheel_for(pkg, built_dist)
        assert wheel, f"stage=metadata package={pkg}: wheel mancante"
        meta = _wheel_metadata(wheel)
        # Licenza: forma PEP 639 (License-Expression) o legacy (License).
        has_license = bool(meta.get("License-Expression") or meta.get("License"))
        assert has_license, f"stage=metadata package={pkg}: METADATA senza licenza"
        assert meta.get("Project-URL"), f"stage=metadata package={pkg}: METADATA senza Project-URL"
        assert meta.get("Classifier"), f"stage=metadata package={pkg}: METADATA senza Classifier"


# =================================================================================================
# Stage 3 — Install pulito a un comando (venv effimero)
# =================================================================================================

def _branch_reachable() -> bool:
    """Precondizione Stage 3: il branch corrente è raggiungibile su GitHub (push del checkout).

    Verifica che il commit di HEAD esista sul remote `origin` (`git ls-remote`). Se la rete o il
    push mancano → la precondizione è assente e gli stage 3 fanno skip azionabile, NON fallimento.
    """
    if not _uv_available():
        return False
    if shutil.which("git") is None:
        return False
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    if head.returncode != 0:
        return False
    head_sha = head.stdout.strip()
    remote = subprocess.run(
        ["git", "ls-remote", REPO_URL], capture_output=True, text=True, timeout=30,
    )
    if remote.returncode != 0:
        return False
    return head_sha in remote.stdout


def _git_ref() -> str:
    """Ref del checkout corrente per il `git+url` (branch attivo, fallback a HEAD)."""
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    return proc.stdout.strip() or "HEAD"


def _skip_if_branch_unreachable():
    if not _uv_available():
        pytest.skip("uv non in PATH — Stage 3 (install pulito) non eseguibile")
    if not _branch_reachable():
        pytest.skip(
            "branch non raggiungibile su GitHub (non pushato o rete assente) — "
            "Stage 3 install pulito da git+url richiede il checkout su origin"
        )


def _uvx_help(subdir: str, entry_point: str) -> subprocess.CompletedProcess:
    ref = _git_ref()
    source = f"git+{REPO_URL}@{ref}#subdirectory={subdir}"
    return subprocess.run(
        ["uvx", "--from", source, entry_point, "--help"],
        capture_output=True, text=True, timeout=600,
    )


@pytest.mark.parametrize("pkg", USER_FACING)
def test_clean_install_uv(pkg):
    """C3.1/C3.2/C3.4 — `uvx --from git+url#subdir=… <ep> --help` → exit 0 (FR-030/034, GATE)."""
    _skip_if_branch_unreachable()
    entry_point = next(iter(EXPECTED_SCRIPTS[pkg]))
    proc = _uvx_help(PACKAGES[pkg]["subdir"], entry_point)
    # C3.5 — su install fallito il referto nomina package + manager.
    assert proc.returncode == 0, (
        f"stage=clean-install manager=uv package={pkg}: entry-point {entry_point} non disponibile "
        f"(exit {proc.returncode})\n{proc.stderr[-1500:]}"
    )


def test_clean_install_pip_sertor(tmp_path):
    """C3.6/C3.7 — `pip install git+url#subdirectory=packages/sertor` best-effort (DA-P2, FR-033).

    `pip` non conosce il workspace uv: la risoluzione di `sertor-core`/`sertor-install-kit` non è
    garantita. Se fallisce → xfail (limite noto → FEAT-010), MAI un rosso che blocca il merge.
    """
    _skip_if_branch_unreachable()
    venv_dir = tmp_path / "pipvenv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True,
                   capture_output=True, text=True)
    if sys.platform == "win32":
        py = venv_dir / "Scripts" / "python.exe"
    else:
        py = venv_dir / "bin" / "python"
    ref = _git_ref()
    source = f"git+{REPO_URL}@{ref}#subdirectory=packages/sertor"
    proc = subprocess.run(
        [str(py), "-m", "pip", "install", source],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        pytest.xfail(
            "pip non risolve il workspace uv (sertor-core/sertor-install-kit) — FEAT-010"
        )
    # Bonus: se pip risolve, l'entry-point deve rispondere.
    if sys.platform == "win32":
        ep = venv_dir / "Scripts" / "sertor.exe"
    else:
        ep = venv_dir / "bin" / "sertor"
    help_proc = subprocess.run([str(ep), "--help"], capture_output=True, text=True, timeout=120)
    assert help_proc.returncode == 0, "stage=clean-install manager=pip pkg=sertor: entry-point KO"


# =================================================================================================
# Stage 4 — Invarianti preservati
# =================================================================================================

def test_install_does_not_start_indexing():
    """C4.1 — install ≠ run: nessun artefatto di packaging avvia ingestione (FR-050).

    Verifica testuale: i pyproject non dichiarano build-hook custom che eseguano codice a
    install-time (indicizzazione/rete). La build hatchling standard non esegue logica applicativa.
    """
    forbidden = ("[tool.hatch.build.hooks", "build_indexer", "cmdclass", "setup_requires")
    for pkg in PACKAGES:
        raw = (PACKAGES[pkg]["dir"] / "pyproject.toml").read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in raw, (
                f"stage=invariant package={pkg}: pyproject riferisce '{token}' (install≠run)"
            )


def test_no_secrets_in_artifacts():
    """C4.2 — nessun segreto nei file versionati (LICENSE/pyproject/VERSION) (FR-051, SC-009)."""
    files = [REPO_ROOT / "VERSION", REPO_ROOT / "LICENSE"]
    for meta in PACKAGES.values():
        files.append(meta["dir"] / "pyproject.toml")
        lic = meta["dir"] / "LICENSE"
        if lic.is_file():
            files.append(lic)
    for path in files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for hint in SECRET_HINTS:
            assert hint not in text, f"stage=invariant: possibile segreto '{hint}' in {path}"


def test_suite_does_not_import_sertor_core():
    """Principio XI — la verifica NON importa `sertor_core`: esercita gli artefatti, non la lib."""
    text = Path(__file__).read_text(encoding="utf-8")
    import_lines = [
        ln for ln in text.splitlines()
        if re.match(r"\s*(import|from)\s+sertor_core\b", ln)
    ]
    assert not import_lines, f"violato Principio XI: import di sertor_core: {import_lines}"


def test_tmp_path_isolation(tmp_path, built_dist):
    """C4.3/C4.4 — la verifica opera in tmp_path/venv effimeri, non tocca i sorgenti (FR-052)."""
    # built_dist è una dir temporanea distinta dal repo.
    assert REPO_ROOT not in built_dist.parents and built_dist != REPO_ROOT
    # I sorgenti di repo restano intatti: VERSION/LICENSE non vengono riscritti dalla suite.
    assert VERSION_FILE.is_file() and (REPO_ROOT / "LICENSE").is_file()
    # tmp_path è scrivibile e isolato.
    probe = tmp_path / "probe.txt"
    probe.write_text("ok", encoding="utf-8")
    assert probe.read_text(encoding="utf-8") == "ok"
