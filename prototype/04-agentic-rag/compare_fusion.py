"""Confronto: fusione **dual-RAG** (deterministica) vs fusione fatta dall'**LLM**.

Per ogni simbolo confronta due modi di ottenere il contesto codice+doc unito:
- **dual-RAG** — `shared.retrieval.get_context(symbol)`: unisce definizione + codice + chiamanti
  + doc collegati via **grafo/metadati**, in una chiamata **deterministica e senza LLM**;
- **LLM** — l'orchestratore `vanilla` (gpt-5.4-mini) che assembla lo stesso contesto chiamando
  i **tool primitivi** (search_code/docs, find_symbol, who_calls, related_docs) e sintetizzando.

Usa il bundle dual-RAG come **riferimento di copertura**: misura se l'LLM ha ricostruito
definizione / chiamanti / doc, e a quale costo (chiamate-tool, turni). Genera `FUSIONE.md`.

Uso:
    PYTHONPATH=. python 04-agentic-rag/compare_fusion.py            # tutti i simboli
    PYTHONPATH=. python 04-agentic-rag/compare_fusion.py --render-from 04-agentic-rag/fusion_results.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for _p in (HERE, HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import orchestrator  # noqa: E402  (motore vanilla = fusione LLM dai tool primitivi)
from shared import retrieval  # noqa: E402

SYMBOLS = ["OAuth2PasswordBearer", "HTTPException", "APIRouter", "BackgroundTasks"]
PROMPT = ("Dammi il contesto COMPLETO del simbolo `{s}` in questa codebase: (1) in quale file "
          "è definito, (2) chi lo usa/chiama nel codice, (3) quali documenti lo spiegano. "
          "Cita sempre i file.")


def _path(label: str) -> str:
    """'fastapi/x.py:17  class Y' o 'docs/.../y.md  (markdown)' -> path."""
    return label.split(":")[0].split()[0] if label else ""


def _covered(answer: str, paths: list[str]) -> bool:
    a = (answer or "").lower()
    return any(p and p.lower() in a for p in paths)


def run_symbol(symbol: str, max_steps: int) -> dict:
    ref = retrieval.get_context(symbol, max_callers=8, max_docs=6)
    def_paths = [_path(d) for d in ref["definitions"]]
    caller_paths = [_path(c) for c in ref["callers"]]
    doc_paths = [d["path"] for d in ref["docs"]]

    out = orchestrator.run(PROMPT.format(s=symbol), max_steps=max_steps)
    ans, tools = out["answer"], [t["tool"] for t in out["trace"]]
    return {
        "symbol": symbol,
        "ref": {"definitions": ref["definitions"], "code_lines":
                [(c["path"], c["start_line"], c["end_line"]) for c in ref["code"]],
                "callers": ref["callers"], "docs": ref["docs"]},
        "have": {"def": bool(def_paths), "callers": bool(caller_paths), "docs": bool(doc_paths)},
        "llm": {
            "answer": ans, "tools": tools, "steps": out["steps"], "client": out["client"],
            "def": _covered(ans, def_paths),
            "callers": _covered(ans, caller_paths) or ("who_calls" in tools),
            "docs": _covered(ans, doc_paths) or (".md" in (ans or "")),
        },
    }


def _cell(have: bool, llm_ok: bool) -> str:
    if not have:
        return "—"          # niente da coprire (es. simbolo senza chiamanti)
    return "✅" if llm_ok else "❌"


def render(rows: list[dict]) -> str:
    out = [
        "# FUSIONE — dual-RAG vs LLM (documentazione parlante, auto-generata)",
        "",
        "> Generato da `04-agentic-rag/compare_fusion.py`. Confronta due modi di **unire codice e "
        "documentazione** per un simbolo: la **fusione dual-RAG** (`get_context`, deterministica, "
        "0 token LLM) e la **fusione fatta dall'LLM** (assembla dai tool primitivi).",
        "",
        "## Riepilogo: l'LLM ricostruisce ciò che il dual-RAG dà per costruzione?",
        "",
        "Il bundle dual-RAG è il **riferimento**: `✅`=l'LLM l'ha coperto, `❌`=mancato, `—`=non applicabile.",
        "",
        "| Simbolo | def (LLM) | chiamanti (LLM) | doc (LLM) | costo LLM (tool/turni) | costo dual-RAG |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        h, l = r["have"], r["llm"]
        cost_llm = f"{len(l['tools'])} tool / {l['steps']} turni"
        out.append(f"| `{r['symbol']}` | {_cell(h['def'], l['def'])} | {_cell(h['callers'], l['callers'])} "
                   f"| {_cell(h['docs'], l['docs'])} | {cost_llm} | 1 chiamata · **0 token LLM** |")
    out += [
        "",
        "Il dual-RAG copre per costruzione definizione+chiamanti+doc collegati (dove esistono), "
        "in modo deterministico e gratuito. L'LLM può ricostruirli ma dipende dai tool che sceglie "
        "e paga ogni volta; può anche omettere una parte (es. i doc) o fermarsi prima.",
        "",
        "---",
        "",
    ]
    for r in rows:
        ref = r["ref"]
        out += [f"## `{r['symbol']}`", "",
                "### 🧩 dual-RAG — `get_context` (deterministico, 0 LLM)", "",
                f"- **Definizione:** {', '.join(ref['definitions']) or '—'}",
                f"- **Codice:** {', '.join(f'{p}:{a}-{b}' for p, a, b in ref['code_lines']) or '—'}",
                f"- **Chiamanti:** {', '.join(ref['callers']) or '—'}",
                f"- **Doc collegati:** {', '.join(f'{d['path']} ({d['why']})' for d in ref['docs']) or '—'}",
                "",
                f"### 🤖 LLM — `vanilla` ({r['llm']['client']}) assembla dai tool primitivi", "",
                f"**Ha usato:** {' → '.join(f'`{t}`' for t in r['llm']['tools']) or '—'}", "",
                "**Ha risposto:**", "",
                "> " + (r["llm"]["answer"] or "_(vuoto)_").strip().replace("\n", "\n> "), "",
                "---", ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Confronto fusione dual-RAG vs LLM")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("--out", default=str(HERE / "FUSIONE.md"))
    ap.add_argument("--results", default=str(HERE / "fusion_results.json"))
    ap.add_argument("--render-from", default=None, metavar="JSON",
                    help="rigenera la doc dai risultati salvati, senza LLM")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    if args.render_from:
        rows = json.loads(pathlib.Path(args.render_from).read_text(encoding="utf-8"))
        print(f"Re-render da {args.render_from}: {len(rows)} simboli")
    else:
        rows = []
        for s in SYMBOLS:
            r = run_symbol(s, args.max_steps)
            rows.append(r)
            l = r["llm"]
            print(f"[{s:20}] LLM def={l['def']} callers={l['callers']} docs={l['docs']} "
                  f"({len(l['tools'])} tool, {l['steps']} turni)")
        pathlib.Path(args.results).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nRisultati grezzi: {args.results}")

    pathlib.Path(args.out).write_text(render(rows), encoding="utf-8")
    print(f"Doc confronto generata: {args.out}")


if __name__ == "__main__":
    main()
