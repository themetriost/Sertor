"""Evidence builder per derivare gli `entity_types` di GraphRAG dal corpus GIA' indicizzato.

Parte deterministica (niente LLM) del tool `derive-entity-types`: legge gli embedding già
presenti in un indice Chroma (corpus code+doc), fa un campionamento *coverage-aware* dei chunk
di documentazione (k-means sugli embedding → rappresentanti per cluster) e, dal grafo di codice
(AST, GraphML) o in fallback dai metadati, estrae i *kind* strutturali e i simboli centrali.

Produce un "evidence pack" (JSON + Markdown) che la skill/LLM usa per PROPORRE la tassonomia di
entity_types (concetti dal lato doc + simboli coarse dal lato codice) da far approvare all'utente.

Repo-agnostico e config-driven: tutto parametrizzabile via CLI. Dipendenze minime
(chromadb, numpy, networkx); nessun sklearn (k-means implementato in numpy).

Uso tipico:
    PYTHONPATH=. .venv/Scripts/python.exe shared/derive_entity_types.py \
        --collection baseline_azure_large --clusters 14 --per-cluster 4
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import chromadb
import numpy as np

from shared.config import settings

_WS = re.compile(r"\s+")


def _pick_collection(client, preferred: str | None) -> str:
    names = [c.name for c in client.list_collections()]
    if not names:
        raise SystemExit("Nessuna collection nell'indice Chroma indicato.")
    if preferred:
        if preferred not in names:
            raise SystemExit(f"Collection {preferred!r} assente. Disponibili: {names}")
        return preferred
    for pref in ("baseline_azure_large", "baseline_azure_small", "baseline_ollama"):
        if pref in names:
            return pref
    return names[0]


def _l2norm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return x / n


def _kmeans(x: np.ndarray, k: int, seed: int, iters: int = 30):
    """k-means++ su vettori L2-normalizzati (distanza = 1 - cos sim). Ritorna (labels, centroids)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    k = min(k, n)
    # init k-means++
    centers = [int(rng.integers(n))]
    d2 = 1.0 - x @ x[centers[0]]
    for _ in range(1, k):
        probs = np.clip(d2, 0, None)
        s = probs.sum()
        idx = int(rng.integers(n)) if s == 0 else int(rng.choice(n, p=probs / s))
        centers.append(idx)
        d2 = np.minimum(d2, 1.0 - x @ x[idx])
    C = x[centers].copy()
    labels = np.zeros(n, dtype=int)
    for _ in range(iters):
        sims = x @ C.T                       # (n, k) cosine sim
        new = sims.argmax(axis=1)
        if np.array_equal(new, labels):
            labels = new
            break
        labels = new
        for j in range(k):
            members = x[labels == j]
            if len(members):
                v = members.mean(axis=0)
                nv = np.linalg.norm(v)
                C[j] = v / nv if nv else C[j]
    return labels, C


def _clean(text: str, max_chars: int) -> str:
    t = _WS.sub(" ", text).strip()
    return t[:max_chars] + ("…" if len(t) > max_chars else "")


def build_doc_clusters(coll, doc_value: str, source_key: str, k: int,
                       per_cluster: int, max_chars: int, seed: int) -> list[dict]:
    got = coll.get(where={source_key: doc_value},
                   include=["embeddings", "documents", "metadatas"])
    embs = np.asarray(got["embeddings"], dtype=np.float64)
    if len(embs) == 0:
        return []
    x = _l2norm(embs)
    labels, C = _kmeans(x, k, seed)
    docs, metas = got["documents"], got["metadatas"]
    clusters: list[dict] = []
    for j in range(len(C)):
        idx = np.where(labels == j)[0]
        if len(idx) == 0:
            continue
        sims = x[idx] @ C[j]
        order = idx[np.argsort(-sims)]          # rappresentanti = più vicini al centroide
        reps = [{"path": metas[i].get("path", "?"), "text": _clean(docs[i], max_chars)}
                for i in order[:per_cluster]]
        paths = Counter(Path(metas[i].get("path", "?")).parent.as_posix() for i in idx)
        clusters.append({
            "size": int(len(idx)),
            "top_dirs": [d for d, _ in paths.most_common(3)],
            "representatives": reps,
        })
    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters


def build_code_evidence(graph_path: Path, coll, code_value: str,
                        source_key: str, top_n: int) -> dict:
    if graph_path.exists():
        import networkx as nx
        G = nx.read_graphml(graph_path)
        kinds = Counter(d.get("kind", "?") for _, d in G.nodes(data=True))
        deg = dict(G.degree())
        syms = [(nid, d) for nid, d in G.nodes(data=True)
                if d.get("kind") in ("class", "function", "method")]
        syms.sort(key=lambda kv: deg.get(kv[0], 0), reverse=True)
        top = [{"name": d.get("name"), "kind": d.get("kind"),
                "degree": int(deg.get(nid, 0)), "path": d.get("path")}
               for nid, d in syms[:top_n]]
        return {"source": f"AST graph ({graph_path.name})",
                "kind_counts": dict(kinds), "top_symbols": top}
    # fallback: solo conteggio dai metadati dei chunk di codice
    got = coll.get(where={source_key: code_value}, include=["metadatas"])
    langs = Counter(m.get("language", "?") for m in got["metadatas"])
    files = {m.get("path") for m in got["metadatas"]}
    return {"source": "metadati chunk (grafo AST assente)",
            "code_chunks": len(got["metadatas"]), "files": len(files),
            "languages": dict(langs)}


def render_md(evidence: dict) -> str:
    L = ["# Evidence pack — derivazione entity_types", "",
         f"- Indice: `{evidence['index_path']}` · collection: `{evidence['collection']}`",
         f"- Doc chunk: {evidence['doc_chunks']} → {len(evidence['doc_clusters'])} cluster · "
         f"Code: {evidence['code']['source']}", ""]
    L.append("## Lato CODICE (strutturale, deterministico)")
    code = evidence["code"]
    if "kind_counts" in code:
        L.append(f"- Kind dei nodi (AST): {code['kind_counts']}")
        L.append("- Simboli più centrali (per grado):")
        for s in code["top_symbols"]:
            L.append(f"  - `{s['name']}` ({s['kind']}, deg={s['degree']}) — {s['path']}")
    else:
        L.append(f"- {code}")
    L += ["", "## Lato DOC (temi dai cluster di embedding)", ""]
    for i, c in enumerate(evidence["doc_clusters"]):
        L.append(f"### Cluster {i} — {c['size']} chunk · dir: {', '.join(c['top_dirs'])}")
        for r in c["representatives"]:
            L.append(f"- [{r['path']}] {r['text']}")
        L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index-path", default=str(settings.index_dir))
    ap.add_argument("--collection", default=None)
    ap.add_argument("--source-key", default="source")
    ap.add_argument("--doc-value", default="doc")
    ap.add_argument("--code-value", default="code")
    ap.add_argument("--graph", default=str(settings.graph_path))
    ap.add_argument("--clusters", type=int, default=14)
    ap.add_argument("--per-cluster", type=int, default=4)
    ap.add_argument("--top-symbols", type=int, default=20)
    ap.add_argument("--max-chars", type=int, default=600)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(settings.root / "03-graphrag" / "entity_types_evidence"))
    args = ap.parse_args()

    client = chromadb.PersistentClient(path=args.index_path)
    name = _pick_collection(client, args.collection)
    coll = client.get_collection(name)

    doc_clusters = build_doc_clusters(coll, args.doc_value, args.source_key,
                                      args.clusters, args.per_cluster, args.max_chars, args.seed)
    code = build_code_evidence(Path(args.graph), coll, args.code_value, args.source_key, args.top_symbols)
    n_doc = sum(c["size"] for c in doc_clusters)

    evidence = {
        "index_path": args.index_path, "collection": name,
        "doc_chunks": n_doc, "doc_clusters": doc_clusters, "code": code,
    }
    out = Path(args.out)
    out.with_suffix(".json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".md").write_text(render_md(evidence), encoding="utf-8")
    print(f"collection={name} doc_chunks={n_doc} clusters={len(doc_clusters)} code={code['source']}")
    print(f"evidence -> {out.with_suffix('.md')}  +  {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
