"""Riepilogo del run GraphRAG (Tappa 3C): token effettivi + struttura del grafo.

Legge le metriche (jsonl) e gli artefatti parquet in `grag/output/`.
Eseguire col venv isolato: 03-graphrag/.venv-grag/Scripts/python.exe 03-graphrag/summarize.py
"""
import glob
import json
from pathlib import Path

import pandas as pd

ROOT = Path("03-graphrag/grag")
OUT = ROOT / "output"


def banner(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


# --- Token / metriche -------------------------------------------------------
banner("TOKEN & METRICHE (ground truth dal metrics writer di GraphRAG)")
jsonl = sorted(glob.glob(str(ROOT / "metrics" / "*.jsonl")))
grand = {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0, "calls": 0}
for fp in jsonl:
    for line in Path(fp).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        m = rec["metrics"]
        pt = int(m.get("prompt_tokens", 0))
        ct = int(m.get("completion_tokens", 0))
        tt = int(m.get("total_tokens", 0))
        cost = float(m.get("total_cost", 0.0))
        calls = int(m.get("successful_response_count", 0))
        retries = int(m.get("retries", 0))
        print(f"\n{rec['id']}:")
        print(f"   chiamate={calls}  retries={retries}  retry_rate={m.get('retry_rate', 0):.2f}")
        print(f"   prompt={pt:,}  completion={ct:,}  total={tt:,}")
        print(f"   cost(registry litellm)=${cost:.4f}")
        grand["prompt"] += pt
        grand["completion"] += ct
        grand["total"] += tt
        grand["cost"] += cost
        grand["calls"] += calls

print("\n--- TOTALE ---")
print(f"   chiamate={grand['calls']:,}")
print(f"   prompt={grand['prompt']:,}  completion={grand['completion']:,}  total={grand['total']:,}")
print(f"   cost(registry litellm)=${grand['cost']:.4f}")


# --- Struttura del grafo ----------------------------------------------------
banner("STRUTTURA DEL GRAFO (artefatti parquet)")


def load(name):
    fp = OUT / f"{name}.parquet"
    return pd.read_parquet(fp) if fp.exists() else None


for name in ["documents", "text_units", "entities", "relationships",
             "communities", "community_reports"]:
    df = load(name)
    print(f"{name:20s} righe={0 if df is None else len(df):>6}")

ent = load("entities")
if ent is not None and "type" in ent.columns:
    banner("DISTRIBUZIONE TIPI DI ENTITA'")
    print(ent["type"].value_counts().to_string())

if ent is not None:
    deg_col = "degree" if "degree" in ent.columns else ("frequency" if "frequency" in ent.columns else None)
    if deg_col:
        banner(f"TOP 15 ENTITA' per {deg_col}")
        cols = [c for c in ["title", "type", deg_col] if c in ent.columns]
        print(ent.sort_values(deg_col, ascending=False)[cols].head(15).to_string(index=False))

rel = load("relationships")
if rel is not None:
    banner("ESEMPI DI RELAZIONI (prime 10 per weight)")
    wcol = "weight" if "weight" in rel.columns else ("combined_degree" if "combined_degree" in rel.columns else None)
    cols = [c for c in ["source", "target", wcol] if c and c in rel.columns]
    show = rel.sort_values(wcol, ascending=False) if wcol else rel
    print(show[cols].head(10).to_string(index=False))

cr = load("community_reports")
if cr is not None and len(cr):
    banner("COMMUNITY REPORTS — titoli (primi 12)")
    tcol = "title" if "title" in cr.columns else cr.columns[0]
    for t in cr[tcol].head(12):
        print(" -", t)
