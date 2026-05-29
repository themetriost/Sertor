"""Eval comparativa dell'Agentic RAG: confronta i framework **a parità** di tool e prompt.

Esegue un eval set di task (`eval_tasks.json`) attraverso ogni motore (`vanilla`,
`autogen`, ...) e misura:
- **cited**: la risposta finale cita un file atteso (segnale di successo end-to-end);
- **passi** e **n° tool** usati (efficienza/strategia).

Oltre alle metriche su stdout, **genera la "documentazione parlante"** in stile `ESEMPI.md`
("ho chiesto X → l'agente ha fatto Y → mi ha risposto Z"), un file Markdown divulgativo.

Uso:
    PYTHONPATH=. python 04-agentic-rag/evaluate.py                     # tutti i task, vanilla+autogen
    PYTHONPATH=. python 04-agentic-rag/evaluate.py --engines vanilla --limit 3
    PYTHONPATH=. python 04-agentic-rag/evaluate.py --out 04-agentic-rag/ESEMPI-agentic.md

Il modello segue `RAG_BACKEND` (local → Ollama `OLLAMA_CHAT_MODEL`, azure → deployment).
Operazione **a pagamento** se `RAG_BACKEND=azure`.
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

import orchestrator  # noqa: E402  (motore vanilla)

TASKS = json.loads((HERE / "eval_tasks.json").read_text(encoding="utf-8"))


def _run_engine(engine: str, question: str, max_steps: int) -> dict:
    """Normalizza l'output dei diversi motori in {answer, tools, steps, client}."""
    if engine == "vanilla":
        out = orchestrator.run(question, max_steps=max_steps)
        tools = [t["tool"] for t in out["trace"]]
        return {"answer": out["answer"], "tools": tools, "steps": out["steps"], "client": out["client"]}
    if engine == "autogen":
        import autogen_app  # import pigro: richiede il pacchetto autogen
        out = autogen_app.run(question, max_steps=max_steps)
        tools = [t["tool"] for t in out["trace"]]
        # `steps` = turni LLM reali (round di tool + sintesi), confrontabile con vanilla
        return {"answer": out["answer"], "tools": tools,
                "steps": out.get("steps", len(tools)), "client": out["client"]}
    if engine == "sk":
        import sk_app  # import pigro: richiede semantic-kernel
        out = sk_app.run(question, max_steps=max_steps)
        tools = [t["tool"] for t in out["trace"]]
        return {"answer": out["answer"], "tools": tools,
                "steps": out.get("steps", len(tools)), "client": out["client"]}
    if engine == "langgraph":
        import langgraph_app  # import pigro: richiede langgraph + langchain-openai
        out = langgraph_app.run(question, max_steps=max_steps)
        tools = [t["tool"] for t in out["trace"]]
        return {"answer": out["answer"], "tools": tools,
                "steps": out.get("steps", len(tools)), "client": out["client"]}
    raise ValueError(f"motore sconosciuto: {engine}")


def _cited(answer: str, expected_files: list[str]) -> bool:
    a = (answer or "").lower()
    return any(ef.lower() in a for ef in expected_files)


def _fmt_tools(tools: list[str]) -> str:
    if not tools:
        return "_nessuno strumento_"
    return " → ".join(f"`{t}`" for t in tools)


def _score(r: dict, task: dict) -> dict:
    """(Ri)calcola cited/tool_ok di una riga rispetto alla ground-truth del task. Senza LLM."""
    exp_tools = task.get("expected_tools", [])
    r["cited"] = _cited(r["answer"], task["expected_files"])
    r["tool_ok"] = (not exp_tools) or any(t in r["tools"] for t in exp_tools)
    r.update(task_id=task["id"], question=task["question"],
             expected_files=task["expected_files"], expected_tools=exp_tools,
             type=task.get("type", ""))
    return r


def evaluate(engines: list[str], tasks: list[dict], max_steps: int) -> list[dict]:
    rows = []
    for task in tasks:
        for engine in engines:
            try:
                r = _run_engine(engine, task["question"], max_steps)
                r["error"] = None
            except Exception as e:  # noqa: BLE001
                r = {"answer": "", "tools": [], "steps": 0, "client": engine, "error": str(e)}
            r["engine"] = engine
            _score(r, task)
            rows.append(r)
            mark = "ERR" if r["error"] else ("OK " if r["cited"] else "miss")
            tmark = "" if not r["expected_tools"] else (" tool✓" if r["tool_ok"] else " tool✗")
            print(f"[{mark}] {engine:8} · {task['id']:18} · passi={r['steps']} tool={len(r['tools'])}{tmark}")
    return rows


def rescore(rows: list[dict], tasks: list[dict]) -> list[dict]:
    """Ri-calcola i punteggi di righe già eseguite (da cache) sulla ground-truth corrente."""
    by_id = {t["id"]: t for t in tasks}
    return [_score(r, by_id[r["task_id"]]) for r in rows if r.get("task_id") in by_id]


def _metrics_table(rows: list[dict], engines: list[str]) -> str:
    lines = ["| Motore | task | cita atteso | tool giusto | passi medi | tool medi |",
             "|---|---|---|---|---|---|"]
    for e in engines:
        er = [r for r in rows if r["engine"] == e]
        n = len(er) or 1
        cited = sum(1 for r in er if r["cited"])
        tool_ok = sum(1 for r in er if r.get("tool_ok"))
        avg_steps = sum(r["steps"] for r in er) / n
        avg_tools = sum(len(r["tools"]) for r in er) / n
        lines.append(f"| `{e}` | {len(er)} | {cited}/{len(er)} | {tool_ok}/{len(er)} | "
                     f"{avg_steps:.1f} | {avg_tools:.1f} |")
    return "\n".join(lines)


def render_doc(rows: list[dict], engines: list[str], tasks: list[dict]) -> str:
    """Genera la documentazione parlante in stile ESEMPI.md."""
    out = [
        "# ESEMPI — Agentic RAG (documentazione parlante, auto-generata)",
        "",
        "> **File generato** da `04-agentic-rag/evaluate.py` (non modificare a mano). Mostra, per ogni",
        "> domanda e per ogni motore, *cosa ho chiesto → cosa ha fatto l'agente → cosa mi ha risposto*.",
        "> È la controparte divulgativa di [`ESEMPI.md`](../ESEMPI.md) per la Tappa 04.",
        "",
        "## Riepilogo (a parità di tool e prompt)",
        "",
        _metrics_table(rows, engines),
        "",
        "- **cita atteso**: la risposta finale nomina il file giusto (successo end-to-end).",
        "- **tool giusto**: l'agente ha usato almeno uno strumento ideale per quel tipo di task.",
        "- I motori condividono `tools.py` e il system prompt: le differenze sono di **orchestrazione**.",
        "- ⚠️ **`passi`**: per `vanilla`/`autogen` sono turni LLM reali; per `sk` è *approssimato* "
        "(SK non espone i confini dei turni: vale ≈ n° tool + 1). Per il **costo** confronta `tool medi`.",
        "- ⚠️ I modelli non sono perfettamente deterministici: i numeri variano tra run; "
        "conta la *tendenza* (es. quale motore sceglie i tool giusti, e quanto è verboso).",
        "",
        "---",
        "",
    ]
    by_task = {t["id"]: t for t in tasks}
    for tid in [t["id"] for t in tasks]:
        task = by_task[tid]
        trows = [r for r in rows if r["task_id"] == tid]
        if not trows:
            continue
        ideal = ", ".join(f"`{t}`" for t in task.get("expected_tools", [])) or "—"
        out += [f"## «{task['question']}»",
                "",
                f"> **Tipo:** {task.get('type', '—')} · **Atteso:** la risposta cita "
                f"`{'` o `'.join(task['expected_files'])}` · **strumenti ideali:** {ideal}",
                ""]
        for r in trows:
            if r["error"]:
                out += [f"### 🤖 {r['engine']}", "", f"⚠️ errore: {r['error']}", ""]
                continue
            esito = "✅ ha citato il file atteso" if r["cited"] else "❌ non ha citato il file atteso"
            if r.get("expected_tools"):
                esito += " · strumento giusto " + ("✅" if r.get("tool_ok") else "❌")
            answer = (r["answer"] or "_(nessuna risposta)_").strip().replace("\n", "\n> ")
            out += [
                f"### 🤖 {r['engine']}  ·  _{r['client']}_",
                "",
                f"**Ha fatto:** {_fmt_tools(r['tools'])}",
                "",
                "**Ha risposto:**",
                "",
                f"> {answer}",
                "",
                f"**Esito:** {esito} · {r['steps']} {'passo' if r['steps'] == 1 else 'passi'}"
                f" · {len(r['tools'])} {'strumento' if len(r['tools']) == 1 else 'strumenti'}",
                "",
            ]
        out += ["---", ""]
    return "\n".join(out)


def main() -> None:
    # Su Windows lo stdout rediretto usa cp1252 e non codifica i simboli/emoji: forza UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    ap = argparse.ArgumentParser(description="Eval comparativa Agentic RAG + doc parlante")
    ap.add_argument("--engines", default="vanilla,autogen,sk,langgraph", help="motori separati da virgola")
    ap.add_argument("--no-merge", action="store_true",
                    help="non fondere con la cache esistente (default: i motori non rieseguiti restano in cache)")
    ap.add_argument("--limit", type=int, default=0, help="esegui solo i primi N task (0 = tutti)")
    ap.add_argument("--max-steps", type=int, default=5)
    ap.add_argument("--out", default=str(HERE / "ESEMPI-agentic.md"), help="file Markdown da generare")
    ap.add_argument("--results", default=str(HERE / "eval_results.json"),
                    help="dove salvare/leggere i risultati grezzi (cache per re-score senza LLM)")
    ap.add_argument("--render-from", metavar="RESULTS_JSON", default=None,
                    help="NON esegue l'LLM: ri-calcola i punteggi e rigenera la doc dai risultati salvati")
    args = ap.parse_args()

    if args.render_from:  # solo re-score + render, gratis (nessuna chiamata LLM)
        rows = json.loads(pathlib.Path(args.render_from).read_text(encoding="utf-8"))
        rows = rescore(rows, TASKS)
        engines = sorted({r["engine"] for r in rows})
        tasks = [t for t in TASKS if any(r["task_id"] == t["id"] for r in rows)]
        print(f"Re-score da {args.render_from}: {len(rows)} righe, motori {', '.join(engines)}")
    else:
        engines = [e.strip() for e in args.engines.split(",") if e.strip()]
        tasks = TASKS[: args.limit] if args.limit else TASKS
        print(f"Eval: {len(tasks)} task × {len(engines)} motori ({', '.join(engines)})\n")
        rows = evaluate(engines, tasks, args.max_steps)
        # merge incrementale: conserva i risultati dei motori NON rieseguiti (eval per-motore senza re-spend)
        p = pathlib.Path(args.results)
        if p.exists() and not args.no_merge:
            try:
                prev = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                prev = []
            kept = [r for r in prev if r.get("engine") not in set(engines)]
            rows = rescore(kept, TASKS) + rows  # riallinea i vecchi alla ground-truth corrente
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nRisultati grezzi salvati: {args.results}")
        engines = sorted({r["engine"] for r in rows})  # render/metriche su tutti i motori in cache

    print("\n" + _metrics_table(rows, engines))
    doc = render_doc(rows, engines, tasks)
    pathlib.Path(args.out).write_text(doc, encoding="utf-8")
    print(f"\nDoc parlante generata: {args.out}")


if __name__ == "__main__":
    main()
