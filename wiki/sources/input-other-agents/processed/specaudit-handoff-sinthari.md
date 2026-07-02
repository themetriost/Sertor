# Handoff: SpecAudit → pacchetto `sertor-flow` (da Sinthari)

Brief self-contained per promuovere **SpecAudit** (sviluppato e validato in Sinthari) a capacità
distribuita dal pacchetto **`packages/sertor-flow`**, così che venga installata col flow come
`requirements` / `speckit-*` / `speclift`. È il **gemello di SpecLift** e la **seconda** skill del flow
con un runtime (SpecLift è stata la prima).

## Cos'è SpecAudit

Dato un **requisito originale** (da `requirements/`, un'altra spec, o EARS di un'altra pipeline) e
l'**output ancorato di SpecLift** per lo stesso changeset, SpecAudit emette **un verdetto per requisito**
— **SODDISFATTO / PARZIALE / MANCANTE / DRIFTED / NON_DOCUMENTATO** — con confidenza e **citazione
dell'àncora SpecLift**, **senza mai leggere codice, test o CI**. È la *back-translation* del gate del
pre-merge: SpecLift traduce il codice in requisiti (bottom-up), SpecAudit confronta col requisito
originale (top-down) e certifica dove convergono e dove divergono.

**Architettura — "sandwich con l'agente al centro" (come SpecLift), MA senza moat filesystem.** Due
marce deterministiche con l'agente al centro:
  - `specaudit prepare --speclift <*.speclift.json> --requirements <dir>` → recupera i due insiemi
    (requisiti originali estratti da `requirements/` + item SpecLift ancorati), li **indicizza**, e
    emette `audit-bundle.json` (autoconsistente + gap dichiarati);
  - l'**agente** legge il bundle, **allinea** (N:M) e **classifica** i verdetti referenziando gli item
    **per indice**, e scrive `adjudicated.json`;
  - `specaudit report --bundle .. --adjudicated ..` → **verifica** integrità e completezza (fail-loud),
    **attacca le àncore dal bundle** (mai riverificate), calcola matrice + scoring di rischio, propaga i
    gap, ed emette il report (JSON canonico + Markdown).
C'è anche un monolite `specaudit audit` (StubAdjudicator) per uso offline/test.

**Il moat è STRUTTURALE, non filesystem** (SpecAudit non tocca il codice): il runtime garantisce
l'onestà — citazione dell'àncora copiata dal bundle per indice (l'agente non può inventarla),
**completezza** (nessun requisito/item scartato in silenzio → fail-loud), **integrità dei riferimenti**
(indice inesistente → fail-loud), guard sulla confidenza, fail-loud su artefatti mancanti/di versione/
changeset non corrispondente. La qualità del *giudizio* (allineamento + verdetto) è dell'agente — è il
moat di giudizio, non riproducibile in codice.

## Dove sta il lavoro

Repo: **github.com/themetriost/Sinthari** (mergiato in `master`, **PR #8**, merge `91c5a45`). Artefatti:
  - Runtime CLI:   `src/specaudit/` + `pyproject.toml` (console-script `specaudit`, secondo package
                   accanto a `src/speclift/`, stessa distribuzione)
  - Skill sottile: `skills/specaudit/SKILL.md` (host-agnostica, sorgente canonico)
  - Contratti:     `specs/002-specaudit-mvp/contracts/` (`cli.md`, `adjudicator-port.md`,
                   `audit-bundle.schema.json`, `adjudication.schema.json`, `output.schema.json`) +
                   `requirements/specaudit/`
  - Test:          `tests/specaudit/` (58 verdi; 180 totali col progetto), ruff pulito,
                   Constitution 11/11 PASS

## Cosa vi chiediamo, mappato su `sertor-flow`

1. **SKILL** (facile, è come `requirements`/`speclift`):
   - aggiungere l'asset
     `packages/sertor-flow/src/sertor_flow/assets/claude/skills/specaudit/SKILL.md`
     (copia di `skills/specaudit/SKILL.md` dal nostro repo);
   - registrarla dove dichiarate le altre skill del flow (manifest / `generate.py` / `sync.py`), così
     entra nel `claude.manifest` con hash e viene installata in `.claude/skills/specaudit/`;
   - il **corpo è già host-agnostico** → riusabile tale e quale per altri assistenti.
2. **RUNTIME** (`specaudit`): è la **seconda** skill del flow con una CLI — il precedente è già vostro
   (SpecLift, feature 084, `packages/speclift`). Applicate **lo stesso stampo** che avete scelto per
   SpecLift (console-script/dipendenza del flow, o pacchetto separato `packages/specaudit`). Nota:
   `specaudit` **NON** dipende dal RAG né da `git` (non legge codice); dipende solo dai due artefatti in
   input (un `*.speclift.json` + una fonte `requirements/`).
3. **CLAUDE.md** (opzionale): un blocco marcato `<!-- SERTOR:SPECAUDIT-USAGE START/END -->` con l'uso
   (le due marce + ruolo dell'agente-giudice), sullo stile dei vostri blocchi asset.

## Dipendenza da SpecLift (rilevante per validazione/dogfooding)

SpecAudit **consuma l'output di SpecLift** (`*.speclift.json`, contratto `output.schema.json` v1). Per
validarlo/dogfoodarlo end-to-end su Sertor serve un output SpecLift **reale** su un vostro changeset —
quindi SpecLift self-hosted (feature 084) è il prerequisito naturale. Da parte nostra, la validazione
con output reale resta pendente per lo stesso motivo (vedi sotto).

## Vincoli di design da preservare

- Corpo skill host-agnostico (no path d'assistente, no slash-command) → parità.
- **Confine di fiducia (non aggirare):** SpecAudit **non** legge codice/test/CI, **non** riverifica le
  àncore di SpecLift (le cita, ereditando i suoi eventuali errori di retrieval — non li corregge).
- **Moat strutturale:** completezza (niente scarti silenziosi) + integrità dei riferimenti + citazione
  senza riverifica sono garanzie del runtime, fail-loud.
- Verdetto **DRIFTED** sempre marcato *proposto* (mai auto-confermato).
- Fail-loud: output SpecLift assente / versione errata / changeset non corrispondente / adjudication
  incompleta → exit code espliciti (vedi `contracts/cli.md`). Niente fallback silenziosi.
- Scala confidenza/rischio **categorica** (alta/media/bassa); scoring di rischio = severità×rilevabilità
  via matrice in `config.py`.

## Stato / pendenze dichiarate

- **T048** — validazione su Sinthari con un `*.speclift.json` **reale**: pendente (richiede il RAG per
  far girare SpecLift su un changeset di Sinthari e produrre l'output reale).
- **T049** — validazione su Kaelen `feat(011)` con EARS reali di SpecLift: **BLOCKED-EXT** finché il
  self-hosting SpecLift in Sertor non è concluso.
- La pipeline è comunque esercitata end-to-end (StubAdjudicator + adjudication reali scritte a mano nei
  test d'integrazione: casi DRIFTED / MANCANTE / NON_DOCUMENTATO).

## Fuori scope (MVP)

Verifica avversariale / anti-collusione ("chi audita l'auditor"), vocabolario di verdetto formalizzato
(redlining, causale, lettera-vs-spirito), scoring FMEA, drift longitudinale multi-changeset,
remediation, packaging come gate di CI/MCP. Restano nel backlog Should/Could dell'epica.

Razionale e storico nel wiki del repo Sinthari: `wiki/concepts/specaudit.md`,
`wiki/concepts/deterministic-sandwich.md` (variante del moat), `wiki/syntheses/roadmap.md`,
`wiki/log/2026-07-02.md`. Grazie!
