"""Confronta due run GraphRAG (es. entity_types generici vs di dominio).

Legge gli artefatti parquet di due cartelle output e ne confronta struttura
(documenti, text unit, entità, relazioni, community) e la distribuzione dei tipi
di entità. Utile per documentare l'effetto del tuning degli entity_types.

Uso:
    PYTHONPATH=. .venv-grag/Scripts/python.exe 03-graphrag/compare_runs.py \
        --a 03-graphrag/grag/output_run1_generic --a-label generico \
        --b 03-graphrag/grag/output            --b-label dominio
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd


def load(out_dir: Path, name: str):
    fp = out_dir / f"{name}.parquet"
    return pd.read_parquet(fp) if fp.exists() else None


def counts(out_dir: Path) -> dict:
    res = {}
    for name in ["documents", "text_units", "entities", "relationships",
                 "communities", "community_reports"]:
        df = load(out_dir, name)
        res[name] = 0 if df is None else len(df)
    return res


def type_dist(out_dir: Path) -> Counter:
    ent = load(out_dir, "entities")
    if ent is None or "type" not in ent.columns:
        return Counter()
    return Counter(ent["type"].fillna("∅").str.upper())


def top_by_degree(out_dir: Path, n: int):
    ent = load(out_dir, "entities")
    if ent is None:
        return []
    col = "degree" if "degree" in ent.columns else ("frequency" if "frequency" in ent.columns else None)
    if not col:
        return []
    cols = [c for c in ["title", "type", col] if c in ent.columns]
    return ent.sort_values(col, ascending=False)[cols].head(n).to_dict("records")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--a-label", default="A")
    ap.add_argument("--b-label", default="B")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    A, B = Path(args.a), Path(args.b)
    la, lb = args.a_label, args.b_label

    ca, cb = counts(A), counts(B)
    print(f"\n{'metrica':22s} {la:>14s} {lb:>14s}   delta")
    print("-" * 66)
    for k in ca:
        da, db = ca[k], cb[k]
        delta = db - da
        print(f"{k:22s} {da:>14d} {db:>14d}   {delta:+d}")

    for label, out in [(la, A), (lb, B)]:
        td = type_dist(out)
        tot = sum(td.values()) or 1
        print(f"\n=== Distribuzione tipi entità — {label} ({sum(td.values())} entità) ===")
        for t, c in td.most_common():
            print(f"  {t:16s} {c:>5d}  ({100*c/tot:4.1f}%)")

    for label, out in [(la, A), (lb, B)]:
        print(f"\n=== Top {args.top} entità per grado — {label} ===")
        for r in top_by_degree(out, args.top):
            deg = r.get("degree", r.get("frequency", "?"))
            print(f"  {str(r.get('title','?')):28s} {str(r.get('type','?')):14s} deg={deg}")


if __name__ == "__main__":
    main()
