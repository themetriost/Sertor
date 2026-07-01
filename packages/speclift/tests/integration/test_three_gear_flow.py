"""Flusso a TRE marce: `changeset` → (agente localizza via "MCP") → `bundle --changeset/--located`
→ (agente scrive le frasi) → `assemble`.

Percorso alternativo per gli host dove l'agente ha accesso diretto ai tool MCP di Sertor
(`search_code`/`find_symbol`/`who_calls`) ma non alla CLI-vehicle `sertor-rag` — es. il dogfooding
di Sertor su se stesso (vedi `wiki/sources/input-other-agents/sertor-feedback-speclift-cli-to-mcp.md`).
A differenza del percorso di default (`test_two_gear_flow.py`), qui NESSUN `EvidenceLocator` gira
dentro la pipeline: la localizzazione è già stata fatta a monte (simulata qui come farebbe l'agente)
e depositata in `located.json`. Il moat (verifica sul filesystem) resta l'unica garanzia forte,
identico al percorso CLI-locator.
"""

from __future__ import annotations

import json

import pytest

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.adapters.git_diff import GitDiffSource
from speclift.cli import main
from speclift.pipeline import Components

from ._gitfixture import make_repo

pytestmark = pytest.mark.integration


class _UnusedLocator:
    """La marcia `changeset` non tocca mai il locator: se lo facesse, questo test fallirebbe rumoroso."""

    def locate_symbols(self, *a):
        raise AssertionError("changeset non deve localizzare nulla")

    def locate_tests(self, *a):
        raise AssertionError("changeset non deve localizzare nulla")


def _components(repo) -> Components:
    return Components(
        diff_source=GitDiffSource(repo),
        locator=_UnusedLocator(),
        author=StubEarsAuthor(),
        resolver=FilesystemAnchorResolver(repo),
    )


def test_changeset_then_bundle_located_then_assemble(tmp_path):
    fx = make_repo(tmp_path)
    changeset_base = tmp_path / "changeset"
    bundle_base = tmp_path / "out"
    report_base = tmp_path / "report"

    # Marcia 0: emetti il changeset grezzo (nessuna localizzazione, nessun RAG toccato).
    code = main(
        ["changeset", fx.head_sha, "--repo", str(fx.path), "--out", str(changeset_base)],
        components=_components(fx.path),
    )
    assert code == 0
    changeset_file = changeset_base.with_name("changeset.changeset.json")
    changeset_payload = json.loads(changeset_file.read_text(encoding="utf-8"))
    assert changeset_payload["excluded_sources"] == []

    files = changeset_payload["files"]
    assert files, "il changeset deve contenere almeno un file toccato"
    calc = next(f for f in files if f["path"] == "calc.py")
    hunk = calc["hunks"][0]
    assert "multiply" in hunk["candidate_identifiers"]
    assert any("multiply" in line for line in hunk["lines"])  # il diff è leggibile dall'agente

    # L'agente "localizza" via i propri tool MCP: same-file per il simbolo, e il test che lo copre.
    located = {
        "symbols": {"calc.py::multiply": [{"name": "multiply", "path": "calc.py", "line": 4}]},
        "tests": {
            "multiply": [
                {"name": "test_multiply", "path": "test_calc.py", "covers_symbol": "multiply"}
            ]
        },
    }
    located_file = tmp_path / "located.json"
    located_file.write_text(json.dumps(located), encoding="utf-8")

    # Marcia 1 (variante --changeset/--located): assembla il bundle SENZA passare da un locator live.
    code = main(
        [
            "bundle",
            "--changeset",
            str(changeset_file),
            "--located",
            str(located_file),
            "--out",
            str(bundle_base),
        ]
    )
    assert code == 0
    bundle_file = bundle_base.with_name("out.bundle.json")
    payload = json.loads(bundle_file.read_text(encoding="utf-8"))
    items = payload["items"]
    assert items, "il fascicolo deve contenere almeno un item da autorare"
    assert any(it["symbol"] == "multiply" for it in items)

    # L'agente scrive le frasi EARS referenziando gli item per indice (identico al percorso a 2 marce).
    authored = {
        "changeset_ref": payload["changeset_ref"],
        "requirements": [
            {
                "item": it["index"],
                "quota": "implementation",
                "statement": f"The code at {it['file']} SHALL expose the change.",
            }
            for it in items
        ],
        "open_questions": [],
    }
    authored_file = tmp_path / "authored.json"
    authored_file.write_text(json.dumps(authored), encoding="utf-8")

    # Marcia 2: riverifica le àncore sul filesystem reale (il moat) — identica al percorso di default.
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
    assert all(r["anchor"]["status"] == "verified" for r in report["requirements"])
    multiply_reqs = [r for r in report["requirements"] if r["anchor"]["symbol"] == "multiply"]
    assert multiply_reqs and multiply_reqs[0]["anchor"]["test"]["path"] == "test_calc.py"


def test_bundle_rejects_changeset_without_located(tmp_path):
    """`--changeset` senza `--located` (o viceversa) è un errore fail-loud, non un default silenzioso."""
    code = main(["bundle", "--changeset", str(tmp_path / "x.json")])
    assert code == 2


def test_bundle_rejects_changeset_mixed_with_ref(tmp_path):
    """`--changeset` è alternativo a `<ref>`, non componibile con esso."""
    changeset_file = tmp_path / "x.changeset.json"
    changeset_file.write_text("{}", encoding="utf-8")
    located_file = tmp_path / "x.located.json"
    located_file.write_text("{}", encoding="utf-8")
    code = main(["bundle", "HEAD", "--changeset", str(changeset_file), "--located", str(located_file)])
    assert code == 2
