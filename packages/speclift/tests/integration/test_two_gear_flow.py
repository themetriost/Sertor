"""G1 (integration) — flusso a due marce: `bundle` → (agente scrive) → `assemble`.

Simula l'agente chiamante: la CLI emette il fascicolo, il test scrive le frasi referenziando gli item
per indice, la CLI le riassembla e riverifica le àncore sul repo reale (il moat). Locator iniettato
(niente RAG): l'aggancio simbolo/test è deterministico sul filesystem.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.adapters.git_diff import GitDiffSource
from speclift.cli import main
from speclift.domain.models import Symbol, TestRef
from speclift.pipeline import Components

from ._gitfixture import _git, make_repo

pytestmark = pytest.mark.integration


class _Locator:
    """Echeggia un simbolo nel file dell'hunk (same-file → àncora-simbolo) + un test che lo copre."""

    def locate_symbols(self, file_path, identifiers, snippet):
        ids = [i for i in identifiers if i]
        return [Symbol(name=ids[0], path=file_path, line=0)] if ids else []

    def locate_tests(self, symbol):
        return [TestRef(name="test_calc", path="test_calc.py", covers_symbol=symbol.name)]


def _components(repo: Path) -> Components:
    return Components(
        diff_source=GitDiffSource(repo),
        locator=_Locator(),
        author=StubEarsAuthor(),  # non usato dalla marcia bundle
        resolver=FilesystemAnchorResolver(repo),
    )


def test_bundle_then_assemble_end_to_end(tmp_path):
    fx = make_repo(tmp_path)
    bundle_base = tmp_path / "out"
    report_base = tmp_path / "report"

    # Marcia 1: emetti il fascicolo
    code = main(
        ["bundle", fx.head_sha, "--repo", str(fx.path), "--out", str(bundle_base)],
        components=_components(fx.path),
    )
    assert code == 0
    bundle_file = bundle_base.with_name("out.bundle.json")
    payload = json.loads(bundle_file.read_text(encoding="utf-8"))
    items = payload["items"]
    assert items, "il fascicolo deve contenere almeno un item da autorare"

    # L'agente scrive: per ogni item, una frase su quota user_capability
    authored = {
        "changeset_ref": payload["changeset_ref"],
        "requirements": [
            {
                "item": it["index"],
                "quota": "user_capability",
                "statement": f"WHEN the change at {it['file']} applies, the system SHALL expose it.",
            }
            for it in items
        ],
        "open_questions": [],
    }
    authored_file = tmp_path / "authored.json"
    authored_file.write_text(json.dumps(authored), encoding="utf-8")

    # Marcia 2: assembla + riverifica
    code = main(
        [
            "assemble",
            "--bundle",
            str(bundle_file),
            "--authored",
            str(authored_file),
            "--repo",
            str(fx.path),
            "--format",
            "json",
            "--out",
            str(report_base),
        ]
    )
    assert code == 0

    report = json.loads(report_base.with_name("report.speclift.json").read_text(encoding="utf-8"))
    assert len(report["requirements"]) == len(items)
    # tutte le frasi dell'agente sopravvivono al moat (àncore reali e verificate)
    assert all(r["anchor"]["status"] == "verified" for r in report["requirements"])
    # nessun placeholder dello stub: il testo è quello scritto dall'agente
    assert all("[EARS DEMANDATO A SERTOR]" not in r["statement"] for r in report["requirements"])


def test_skipped_item_surfaces_as_drift(tmp_path):
    """G2: se l'agente NON scrive requisiti per un item, quell'item appare come drift proposto."""
    fx = make_repo(tmp_path)
    bundle_base = tmp_path / "out"
    report_base = tmp_path / "report"

    main(
        ["bundle", fx.head_sha, "--repo", str(fx.path), "--out", str(bundle_base)],
        components=_components(fx.path),
    )
    bundle_file = bundle_base.with_name("out.bundle.json")
    items = json.loads(bundle_file.read_text(encoding="utf-8"))["items"]
    assert len(items) >= 2, "serve un bundle multi-item per dimostrare la copertura parziale"

    # L'agente copre SOLO il primo item; gli altri restano scoperti.
    covered = items[0]
    authored = {
        "requirements": [
            {
                "item": covered["index"],
                "quota": "implementation",
                "statement": f"The code at {covered['file']} SHALL behave as changed.",
            }
        ],
        "open_questions": [],
    }
    authored_file = tmp_path / "authored.json"
    authored_file.write_text(json.dumps(authored), encoding="utf-8")

    code = main(
        [
            "assemble",
            "--bundle",
            str(bundle_file),
            "--authored",
            str(authored_file),
            "--repo",
            str(fx.path),
            "--format",
            "json",
            "--out",
            str(report_base),
        ]
    )
    assert code == 0

    report = json.loads(report_base.with_name("report.speclift.json").read_text(encoding="utf-8"))
    assert len(report["requirements"]) == 1  # solo l'item coperto
    assert report["requirements"][0]["anchor"]["file"] == covered["file"]
    drifts = report["drifts"]
    assert len(drifts) == len(items) - 1  # tutti gli item scoperti sono drift
    assert all(d["status"] == "proposed" for d in drifts)


def test_bundle_filters_spec_always_and_docs_by_mode(tmp_path):
    """G3: spec/requisiti sempre fuori; la documentazione entra solo con --include-docs."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# Title\n\nDocs.\n", encoding="utf-8")
    (repo / "specs" / "x").mkdir(parents=True)
    (repo / "specs" / "x" / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init mixed")
    head = _git(repo, "rev-parse", "HEAD")

    def _bundle(out_base, *extra):
        main(
            ["bundle", head, "--repo", str(repo), *extra, "--out", str(out_base)],
            components=_components(repo),
        )
        payload = json.loads(out_base.with_name(out_base.name + ".bundle.json").read_text("utf-8"))
        files = {it["file"] for it in payload["items"]}
        excluded = {p for p, _ in (tuple(e) for e in payload["excluded_sources"])}
        return files, excluded

    # Senza doc: solo il codice; README e spec esclusi.
    files, excluded = _bundle(tmp_path / "nodocs")
    assert "src/app.py" in files
    assert "README.md" not in files
    assert {"README.md", "specs/x/spec.md"} <= excluded

    # Con doc: README incluso; la spec resta SEMPRE fuori.
    files2, excluded2 = _bundle(tmp_path / "withdocs", "--include-docs")
    assert "README.md" in files2
    assert "specs/x/spec.md" in excluded2
    assert "README.md" not in excluded2


def test_assemble_rejects_invented_anchor(tmp_path):
    """Se l'agente referenzia un item inesistente, `assemble` fallisce *loud* (exit 5)."""
    fx = make_repo(tmp_path)
    bundle_base = tmp_path / "out"
    main(
        ["bundle", fx.head_sha, "--repo", str(fx.path), "--out", str(bundle_base)],
        components=_components(fx.path),
    )
    bundle_file = bundle_base.with_name("out.bundle.json")

    authored_file = tmp_path / "authored.json"
    authored_file.write_text(
        json.dumps({"requirements": [{"item": 999, "quota": "behaviour", "statement": "x"}]}),
        encoding="utf-8",
    )

    code = main(
        ["assemble", "--bundle", str(bundle_file), "--authored", str(authored_file), "--repo", str(fx.path)]
    )
    assert code == 5
