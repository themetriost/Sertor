# Research — Documentazione utente MVP (096-doc-utente-mvp)

Phase 0. Risoluzione delle incognite della spec e consolidamento delle decisioni. Poiché è authoring di
documentazione, la «ricerca» è **analisi degli asset reali** (per l'anti-drift) + risoluzione della
DA-4 (tooling di lint per `docs/`).

## Decisione 1 — Strumento di verifica link/lint per `docs/` (DA-4)

- **Decisione:** la verifica dei link della doc utente (`docs/` + `README.md`) è **manuale/scriptata** in
  fase di implement — un controllo che ogni link relativo `[…](….md)` risolva a un file esistente — più
  il walkthrough di accettazione. **Non** si introduce un linter automatico per `docs/` in questa feature.
- **Rationale:** verificato nel repo che **non esiste** oggi un link/lint automatico per `docs/`:
  - `sertor-wiki-tools validate` è la verifica strutturale, ma è **scoped su `wiki/`** (via
    `wiki.config.toml`), non su `docs/`;
  - la CI (`.github/workflows/ci.yml`) esegue pytest + ruff, **non** tocca `docs/`;
  - nessun test/script del repo fa link-checking su `docs/`.
  Introdurre un linter per `docs/` sarebbe una **capacità nuova** (fuori dallo scope di A-18, che è i due
  Must di contenuto) e va oltre il valore dell'MVP.
- **Alternative considerate:** (a) estendere `sertor-wiki-tools validate` a `docs/` — respinta: cambia un
  vehicle, oltre l'M×M dell'item, è materia di una feature dedicata (eventuale E10/E13 follow-up); (b)
  aggiungere un job CI markdown-link-check — respinta per lo stesso motivo (scope creep). **Follow-up
  tracciabile** se emergesse valore: un check link per `docs/` (roadmap/backlog E13 Fase 1 «reference/
  anti-drift» FEAT-008, o E10 igiene).

## Decisione 2 — Esempi CLI: entrambe le varianti affiancate (clarify DA-1)

- **Decisione:** i blocchi comando del getting-started mostrano **entrambe le varianti affiancate** —
  Claude (`--assistant` omesso, default reale) **e** Copilot (`--assistant copilot-cli`) — dove il comando
  diverge. Il **dettaglio pieno** per-assistente resta **delegato** a `install-claude.md`/
  `install-copilot.md` (FR-003), non ricopiato.
- **Rationale:** scelta utente in clarify (2026-07-11). Rende la host-agnosticità **esplicita e visibile**
  (Principio X) invece di privilegiare un assistente; il costo (blocchi un po' più lunghi) è accettato.
- **Alternative considerate:** Claude-default + callout Copilot (più asciutto) — non scelta.

## Decisione 3 — Esempio concreto code+doc: illustrativo generico (clarify DA-2)

- **Decisione:** il «money shot» del differenziatore (in getting-started e README) è una query
  **illustrativa generica e host-agnostica** — es. *«come funziona l'autenticazione?»* → un flusso `docs`
  (la spec/il documento che spiega il *perché*) **e** un flusso `code` (l'handler che dice *cosa fa*) —
  mostrando la forma della tupla `(docs, code)` di `search_combined`. **Non** una query legata al corpus
  interno di Sertor.
- **Rationale:** scelta utente in clarify. La doc è **esterna**: l'utente la legge sul **proprio** repo →
  un esempio ancorato a Sertor sarebbe meno host-agnostico e rischierebbe di esporre nomi/percorsi
  interni (viola la separazione interna/esterna, CS-5). La forma d'output va resa realistica ma
  chiaramente illustrativa (placeholder di path).
- **Alternative considerate:** output reale dal dogfood di Sertor (più «vero» ma Sertor-coupled) — non
  scelto.

## Decisione 4 — Fonti reali dei comandi (anti-drift, FR-012/FR-014)

- **Decisione:** ogni comando mostrato è **copiato** dagli asset/doc reali già verificati:
  - install RAG: `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor"
    sertor install rag [--assistant copilot-cli] [--backend azure|local]` (da `install-claude.md`/
    `install-copilot.md`);
  - configure (solo Azure): `… sertor configure --backend azure` (da `install-claude.md`);
  - index: `uv run --project .sertor sertor-rag index .` (regola `--project`, non `--directory`);
  - query CLI: `uv run --project .sertor sertor-rag search "how does X work?"`;
  - MCP: caricamento `sertor-rag` in `.mcp.json` → `search_code`/`search_docs`/`search_combined` (+ 4 tool
    grafo), con `search_combined` che rende la tupla `(docs, code)` (da `retrieval.md` + MCP server).
- **Rationale:** il default `glove` è zero-config (nessun segreto); Azure richiede `configure`. Il
  prerequisito è Python ≥ 3.11 + `uv`, rete GitHub (`git+url`, no PyPI). Tutto già presente e coerente nei
  doc esistenti → il getting-started **ordina**, non inventa.
- **Nota anti-drift:** se durante la scrittura un comando risultasse errato/obsoleto negli asset, è un
  **finding** (Principio XII), da segnalare, non da «correggere silenziosamente» solo nella doc.

## Sintesi

Tutte le incognite risolte; nessun `NEEDS CLARIFICATION` residuo. Nessuna entità dati né interfaccia
esterna (no `data-model.md`/`contracts/`). Pronto per Phase 1 (quickstart di verifica) e poi
`/speckit-tasks`.
