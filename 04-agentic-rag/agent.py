"""CLI dell'Agentic RAG (orchestratore vanilla).

Uso:
    PYTHONPATH=. python 04-agentic-rag/agent.py "Come funziona OAuth2PasswordBearer e chi lo usa?"
    PYTHONPATH=. python 04-agentic-rag/agent.py "..." --backend azure --max-steps 5 -v
    PYTHONPATH=. python 04-agentic-rag/agent.py "..." --json

Il modello dell'agente è scelto da `RAG_BACKEND` (local → Ollama `OLLAMA_CHAT_MODEL`,
azure → Azure `AZURE_OPENAI_CHAT_DEPLOYMENT`). Vedi `04-agentic-rag/README.md`.
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

import orchestrator  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Agentic RAG su codice + documentazione")
    ap.add_argument("task", help="domanda/obiettivo in linguaggio naturale")
    ap.add_argument("--backend", choices=["local", "azure"], default=None,
                    help="override del backend (default: RAG_BACKEND da .env)")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("-v", "--verbose", action="store_true", help="mostra i tool chiamati")
    ap.add_argument("--json", action="store_true", help="output JSON con la trace completa")
    args = ap.parse_args()

    if args.verbose and not args.json:
        print("== passi dell'agente ==")
    out = orchestrator.run(args.task, max_steps=args.max_steps,
                           backend=args.backend, verbose=args.verbose)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print(f"\n=== RISPOSTA === ({out['client']})\n")
    print(out["answer"])
    tools_used = ", ".join(t["tool"] for t in out["trace"]) or "nessuno"
    print(f"\n— passi: {out['steps']} · tool chiamati: {tools_used}")


if __name__ == "__main__":
    main()
