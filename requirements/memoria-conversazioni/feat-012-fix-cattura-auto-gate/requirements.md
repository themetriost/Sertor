# E4-FEAT-012 — Fix: la cattura automatica non scatta mai (gate privacy sull'ambiente sbagliato)

**Epica:** [`memoria-conversazioni`](../epic.md) · **Tipo:** bug host-facing · **Priorità:** Must
**Stato:** ✅ implementata (2026-07-21) · **Distinta da** [FEAT-011](../fix-cattura-encoding-e-fail-loud/requirements.md) (encoding path con spazi).

## Contesto / difetto

L'hook `memory-capture.py` (SessionEnd) è un thin wrapper che delega a `sertor-rag memory archive`.
Prima di delegare applica un **gate privacy** (`_memory_enabled()`) che legge
`os.environ["SERTOR_MEMORY"]`. Ma il valore `SERTOR_MEMORY=true` vive in **`.sertor/.env`**, che è
caricato **solo** da `Settings.load(override=True)` **dentro la CLI** — **non** iniettato
nell'ambiente del processo hook. Quindi il gate legge sempre `None` → l'hook fa un **no-op
silenzioso** (uscita 0, nessun breadcrumb) prima di invocare la CLI che archivierebbe correttamente.

**Effetto:** su **ogni ospite** che abilita la memoria via file `.sertor/.env` (il layout normale
dell'installer), la cattura automatica **non scatta mai**, in silenzio. La CLI manuale
(`sertor-rag memory archive`) funziona perché legge il `.env` via `Settings`.

**Regressione introdotta** dalla migrazione hook `.ps1`→`.py` (A-09, `69d527c`, 2026-07-09): ha
spostato il gate in Python su `os.environ`. Confermato sul dogfood: ultima sessione auto-catturata =
**2026-07-09**; `os.environ["SERTOR_MEMORY"]` = `None` mentre `.sertor/.env` ha `SERTOR_MEMORY=true`.
Il difetto è nell'**asset distribuito** (`assets/rag/hooks/`), non solo nel dogfood.

## Requisiti (EARS)

- **REQ-001** — QUANDO l'hook `memory-capture` valuta il gate privacy, il sistema DEVE considerare
  abilitata la memoria SE E SOLO SE `SERTOR_MEMORY` risulta *truthy* **dalla stessa fonte che la CLI
  osserva** (il `.env` risolto: `./.env` esplicito, poi `.sertor/.env` ancorato a
  `CLAUDE_PROJECT_DIR`), con fallback a `os.environ` quando il file non porta la chiave.
- **REQ-002** — DOVE il `.env` risolto porta `SERTOR_MEMORY`, il suo valore DEVE prevalere su
  `os.environ` (parità con `Settings.load(override=True)`).
- **REQ-003** — QUANDO né il `.env` né l'ambiente portano un valore *truthy*, il sistema DEVE restare
  un **no-op silenzioso** (default privacy FR-015 preservato: uscita 0, nessuna scrittura).
- **REQ-004** — La correzione DEVE restare **stdlib-only** (gli hook girano via `uv run --no-project`
  su interprete ambientale, senza `python-dotenv`) e **host-agnostica** (parità Claude/Copilot: la
  logica vive in `_hooklib`, byte-copiata in entrambe le copie bundle).

## Fuori scope

- Rifattorizzare il contratto di gate della CLI (`memory archive` continua a gatare via `Settings`).
- Ricognizione R-1 cattura host-specifica (non pertinente: la causa è il gate, non l'adapter).

## Verifica

- Unit (offline, parity suite): `memory_enabled()` legge `.sertor/.env`; `.env` vince su `os.environ`;
  assente → `False`; fallback all'ambiente; `./.env` esplicito consultato per primo.
- LIVE sul dogfood: con `os.environ` privo di `SERTOR_MEMORY`, `memory_enabled()` → `True` dal
  `.sertor/.env` reale; `sertor-rag memory archive` colma il buco (12 sessioni 10→20 luglio).
