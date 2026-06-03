"""Genera una tavola Excalidraw di Sertor: architettura (Clean) + roadmap.

Uso: .venv-core/Scripts/python.exe presentation/build_excalidraw.py
Output: presentation/sertor-architettura-roadmap.excalidraw
Apri il file su https://excalidraw.com (o estensione VS Code) e modificalo a piacere.
Solo stdlib (nessuna dipendenza).
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "sertor-architettura-roadmap.excalidraw"
TS = 1717400000000  # timestamp fisso (determinismo)
_elements: list[dict] = []
_seed = 1000


def _next_seed() -> int:
    global _seed
    _seed += 7
    return _seed


def rect(x, y, w, h, stroke, bg, *, rounded=True, sw=2):
    eid = f"r{len(_elements)}"
    _elements.append({
        "id": eid, "type": "rectangle", "x": x, "y": y, "width": w, "height": h, "angle": 0,
        "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid", "strokeWidth": sw,
        "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 3} if rounded else None, "seed": _next_seed(), "version": 1,
        "versionNonce": _next_seed(), "isDeleted": False, "boundElements": [], "updated": TS,
        "link": None, "locked": False,
    })
    return eid


def text(x, y, s, size, color, *, w=None, align="center"):
    w = w if w is not None else max(80, int(len(max(s.split("\n"), key=len)) * size * 0.6))
    h = int(size * 1.3 * (s.count("\n") + 1))
    _elements.append({
        "id": f"t{len(_elements)}", "type": "text", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": color, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
        "frameId": None, "roundness": None, "seed": _next_seed(), "version": 1,
        "versionNonce": _next_seed(), "isDeleted": False, "boundElements": [], "updated": TS,
        "link": None, "locked": False, "text": s, "fontSize": size, "fontFamily": 2,
        "textAlign": align, "verticalAlign": "top", "containerId": None, "originalText": s,
        "lineHeight": 1.3, "autoResize": True, "baseline": size,
    })


def band(x, y, w, h, stroke, bg, label, sublabel, size=20):
    rect(x, y, w, h, stroke, bg)
    text(x + 16, y + h / 2 - size, label, size, stroke, w=w - 32, align="center")
    if sublabel:
        text(x + 16, y + h / 2 + 6, sublabel, 13, "#5f6b7a", w=w - 32, align="center")


def arrow(x1, y1, x2, y2, color="#1f2a44"):
    _elements.append({
        "id": f"a{len(_elements)}", "type": "arrow", "x": x1, "y": y1,
        "width": abs(x2 - x1), "height": abs(y2 - y1), "angle": 0, "strokeColor": color,
        "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2,
        "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 2}, "seed": _next_seed(), "version": 1, "versionNonce": _next_seed(),
        "isDeleted": False, "boundElements": [], "updated": TS, "link": None, "locked": False,
        "points": [[0, 0], [x2 - x1, y2 - y1]], "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None, "startArrowhead": None, "endArrowhead": "arrow",
    })


# palette
DARK, BLUE, GREEN, AMBER, GREY = "#1f2a44", "#2d6cdf", "#1e8e3e", "#b86e00", "#5f6b7a"
L_BLUE, L_GREEN, L_AMBER, L_GREY, L_DARK = "#eaf1fd", "#e9f6ed", "#fbf1e0", "#eef1f5", "#e7eaf0"

# ---- titolo ----
text(40, 30, "Sertor — architettura & roadmap", 30, DARK, w=900, align="left")
text(40, 72, "Framework RAG repo-agnostico · libreria + CLI + MCP · governance SpecKit", 15, GREY,
     w=900, align="left")

# ---- Cos'è Sertor (definizione) ----
rect(40, 102, 1300, 80, BLUE, L_BLUE)
text(58, 112, "Cos'è Sertor", 15, BLUE, w=1264, align="left")
text(58, 136, "Trasforma qualunque repository (codice + documentazione) in una base di conoscenza "
     "interrogabile in linguaggio naturale: indicizza e recupera i passaggi pertinenti citando il "
     "file. Non genera la risposta finale — fornisce il contesto. Usabile come libreria, CLI o tool MCP.",
     12, DARK, w=1264, align="left")

# ---- Una sola verità: sorgenti + documentazione + wiki coesistono ----
text(40, 200, "Una sola verità: sorgenti + documentazione coesistono in un unico corpus", 18, DARK,
     w=1300, align="left")
chips = [
    (60, "Codice", "come funziona", GREEN, L_GREEN),
    (380, "Documentazione", "il perché (esistente)", AMBER, L_AMBER),
    (700, "Wiki LLM", "il perché (distillato, vive nel repo)", BLUE, L_BLUE),
]
for cx, lab, sub, st, bg in chips:
    band(cx, 232, 290, 62, st, bg, lab, sub, size=16)
    arrow(cx + 145, 296, 700, 362, GREY)
rect(540, 362, 540, 50, DARK, L_DARK)
text(556, 376, "Corpus unico interrogabile — search_code · search_docs · search_combined", 12, DARK,
     w=508, align="center")
text(1095, 238, "indicizzati insieme,\npeso paritario,\ncitando il file", 12, GREY, w=240,
     align="left")

# ---- ARCHITETTURA (sinistra) ----
text(40, 450, "Architettura (Clean Architecture)", 20, DARK, w=560, align="left")
ax, aw = 60, 520
layers = [
    (490, "Consumatori", "CLI `sertor` · Server MCP", BLUE, L_BLUE, 64),
    (566, "Composition root", "wiring da configurazione (.env)", GREY, L_GREY, 54),
    (632, "Adapters", "Ollama/Azure (embeddings,LLM) · Chroma/Azure Search", AMBER, L_AMBER, 64),
    (708, "Services / Engines / Wiki", "ingestione·chunking·indexing·retrieval·baseline·wiki",
     GREEN, L_GREEN, 64),
    (784, "Domain (cuore)", "entità · porte · errori — nessun SDK esterno", DARK, L_DARK, 64),
]
for y, lab, sub, stroke, bg, h in layers:
    band(ax, y, aw, h, stroke, bg, lab, sub)
# frecce: dipendenze verso l'interno
for i in range(len(layers) - 1):
    y_from = layers[i][0] + layers[i][5]
    y_to = layers[i + 1][0]
    arrow(ax + aw + 20, y_from, ax + aw + 20, y_to + 10, GREY)
text(ax + aw + 30, 650, "dipendenze\n→ verso\nl'interno", 12, GREY, w=90, align="left")

# ---- ROADMAP (destra) ----
rx = 700
text(rx, 450, "Roadmap", 20, DARK, w=620, align="left")
cols = [
    ("✓ Fatto (in produzione)", GREEN, L_GREEN,
     ["Nucleo retrieval (FEAT-001)", "Motore baseline (FEAT-002)", "Skill LLM Wiki (FEAT-003)",
      "CLI sertor (index/search/wiki)", "Server MCP (motore nuovo)", "Dogfooding su Azure"]),
    ("▶ Prossimo (Should)", BLUE, L_BLUE,
     ["RAG ibrido + reranking (004)", "RAG a grafo / GraphRAG (005)", "RAG agentico (006)",
      "Manutenzione wiki (007)", "CLI: install selettivo"]),
    ("◌ Dopo (Could/Won't)", GREY, L_GREY,
     ["Arricchimento Wiki↔RAG (008)", "Refresh incrementale (009)", "CLI: wizard config",
      "Distribuzione PyPI"]),
]
cw, gap = 200, 12
for i, (head, stroke, bg, items) in enumerate(cols):
    x = rx + i * (cw + gap)
    rect(x, 490, cw, 44, stroke, stroke)
    text(x + 8, 502, head, 13, "#ffffff", w=cw - 16, align="center")
    rect(x, 544, cw, 330, stroke, bg)
    yy = 564
    for it in items:
        text(x + 12, yy, "• " + it, 12, DARK, w=cw - 24, align="left")
        yy += 46

# ---- footer ----
text(40, 894, "MVP del core (nucleo + baseline + wiki) completo, in produzione e dogfoodato su sé "
     "stesso (Azure). Codice, doc e wiki nello stesso corpus. 9 PR · 108 test · Costituzione 9/9.",
     13, GREY, w=1320, align="left")

scene = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": _elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {},
}
OUT.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OK: {OUT}  ({len(_elements)} elementi)")
