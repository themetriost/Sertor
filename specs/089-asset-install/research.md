# Research — asset-install (Phase 0)

Risoluzione delle decisioni di design e delle domande aperte (spec §Decisioni, requirements §10 DA-1..6).
Ground truth: dry-run empirico 2026-07-04 ([[asset-install-installer-dry-run-2026-07-04]]), codice
installer (`install_wiki.py`, `install_rag.py`, `install_governance.py`, `claude_md.py`, `sync.py`,
`wiki_tools/structure.py`), stato EOL del repo (`git ls-files --eol`).

---

## D1 — Policy line-ending (DD-1 / FR-005 / E15-FEAT-010)

- **Decisione:** **(A) normalizzare tutto a LF.** `.gitattributes` con `* text=auto eol=lf` in **tre
  posti**: (1) radice del dogfood; (2) bundle `assets/` dei package installer (rinormalizzati a LF così le
  guardie byte confrontano LF↔LF); (3) **template installer** (host-facing, deposto da `sertor install
  wiki`/`rag` sull'ospite → beneficia ogni host Windows).
- **Rationale:** l'installer scrive CRLF su Windows; i sorgenti dogfood sono LF (verificato: `CLAUDE.md`
  `i/lf w/lf`). Senza policy, un ri-scrittura via installer gonfia il diff (dry-run: `CLAUDE.md` 1228 righe
  vs **174 reali**) → review impossibile, mina l'ispezionabilità (Principio XII). LF è il default naturale
  dei sorgenti e no-op sugli host Unix (Edge Case «host non-Windows»).
- **Meccanica:** aggiungere `.gitattributes`, poi `git add --renormalize .` per allineare l'index; verificare
  con `git ls-files --eol` che il repo sia consistente (SC-2). La normalizzazione vale **su dogfood + bundle
  insieme** (Edge Case «CRLF↔byte-guard»): normalizzare solo il dogfood romperebbe la guardia byte.
- **Alternative scartate:** (B) CRLF coerente ovunque — innaturale per i sorgenti, contro convenzione;
  (C) rendere le guardie byte EOL-insensibili — nasconde il churn invece di rimuoverlo (anti-XII).
- **Implicazione host:** modifica host-facing → gate «feature = installabile su ospite» + **doc utente**
  (`docs/install.md` + quick-start) aggiornati nello stesso step (regola CLAUDE.md §Feature completa 3).

## D2 — CLAUDE.md bilingue (DD-2)

- **Decisione:** **accettato** — `CLAUDE.md` del dogfood è **bilingue per costruzione**: i blocchi marker
  restano **EN** (host-agnostici, come tutti gli asset distribuiti — Principio X), la prosa dogfood resta
  **IT** (governance interna del dogfood). Non è un difetto: è la sovrapposizione client-form + dogfood-form.
- **Rationale:** i blocchi sono asset distribuiti → devono restare EN e generici; tradurli romperebbe la
  parità byte con l'ospite. La prosa IT è il contratto di governance letto a ogni sessione. Convivono.

## D3 — Riconciliazione marker-block vs prosa (DA-1 / FR-003/004) — **ibrido per-blocco**

Il dry-run e il codice confermano: `write_marker_block`/`update_marker_block` sono **già idempotenti**
(replace-if-marker, byte-for-byte fuori dai marker, D4). Quindi il problema **non è block-vs-block** (un
ri-install non duplica un blocco già presente coi marker), ma **block-vs-prosa hand-written**: la prosa
dogfood copre già gli stessi temi → duplicazione semantica. Riconciliazione = **contenuto**, non codice.

- **Decisione (ibrido per-blocco, confermata utente):**
  - **`SERTOR:RAG-USAGE`** → **tieni-blocco**, prosa quasi intatta. Il blocco è il proprietario di quella
    sezione (disciplina MCP-first host-facing); la prosa dogfood che la duplica pura si sfronda al minimo.
  - **`SERTOR:WIKI-RITUAL`** → **prosa-vince**. La prosa dogfood è nettamente più ricca (~10 punti vs 4 del
    blocco): valutare la **rimozione del blocco** dal `CLAUDE.md` del dogfood (o tenerlo minimale) evitando
    la ridondanza; la conoscenza resta nella prosa IT.
  - **`SERTOR:SDLC-RITUAL`** → **ibrido vero**: tieni il blocco (esplicita le 7 fasi SpecKit in forma-client)
    e **sfronda dalla prosa i duplicati puri**, lasciando nella prosa solo ciò che il blocco non dice.
- **Invariante (SC-3):** ogni tema di governance (RAG usage · rituale wiki · SDLC/git) è coperto **una sola
  volta** (blocco **o** prosa), verificabile con un conteggio marker/sezioni; un ri-install non re-inserisce.
- **Alternative scartate:** (a) installer preservante sul block (non serve: già idempotente); (c) dichiarare
  tutta la prosa divergenza-dev (perde la fedeltà «dogfood = client» sui blocchi).
- **Nota Principio X:** questa riconciliazione tocca **solo `CLAUDE.md` del dogfood**, non un asset
  distribuito → non è uno special-case negli asset; è lo stato del dogfood che adotta la forma-client.

## D4 — Ordine di esecuzione dei 3 installer (DA-2)

- **Decisione:** **`sertor-flow install` → `sertor install rag` → `sertor install wiki`**.
- **Rationale:** `sertor-flow install` materializza la machinery SpecKit + il blocco SDLC (`specify init
  --force`, preservante su costituzione/`plan-template` via FEAT-005) → è il più «strutturale» e va prima;
  `install rag` deposita hook/skill/agenti RAG + wiring `settings.json` PreToolUse + blocco RAG-USAGE +
  `.sertor/sertor-cli-reference.md`; `install wiki` deposita struttura wiki + blocco WIKI-RITUAL. `rag` e
  `wiki` toccano `settings.json`/`CLAUDE.md` in modo additivo-idempotente (merge, non overwrite) → l'ordine
  fra loro non è critico, ma questo è il più leggibile. Verificato dal dry-run: nessuna interazione
  distruttiva fra i tre.
- **Chi tocca cosa:** `settings.json` ← rag (+ eventuali hook wiki); `CLAUDE.md` ← tutti e tre (blocchi
  distinti, marker disgiunti); `.specify/` ← flow; `wiki/` ← wiki; `.sertor/` ← rag.

## D5 — Verifica della corrispondenza post-install (DA-3 / contratto)

- **Decisione:** **riusare le guardie byte esistenti** (FEAT-002) come rete anti-drift, valutate ora
  sull'esito del **processo reale** (non del sync), + un **test di idempotenza** (due esecuzioni → no diff
  distruttivo) + un **test negativo EOL** (`tests/unit/test_asset_install_eol.py`) che fallisce se il repo
  torna EOL-inconsistente o se un file toccato dall'install mostra churn. Nessun nuovo harness CI pesante:
  la CI gira già la suite completa (gate E15-FEAT-008).
- **Rationale:** le guardie byte esistono e sono esaustive (`test_assets_rag_dogfood_sync` enumera **ogni**
  asset byte-copiato); il loro ruolo si sposta da «prova che il sync ha copiato» a «prova che dogfood ==
  ciò che l'ospite riceve», indipendente da chi ha depositato. NFR-1 (idempotenza verificata, non assunta).

## D6 — E15-FEAT-009 (`.mcp.json` `--directory`→`--project`) è una dipendenza? (DA-5)

- **Decisione:** **NO dipendenza.** FEAT-009 è **chiusa not-a-bug** (2026-07-04): `registered=False` era
  artefatto della `cwd` del comando `doctor`, non del template; `Settings.load` è self-localizing. Il dry-run
  ha confermato `.mcp.json` **preservato** (merge salta se il server esiste). Nessun fix da anteporre.

## D7 — Residui non-byte con dest gitignorata (DA-6 / FR-007 / SC-5)

- **Decisione:** i residui che l'install produce con dest **gitignorata** (`.sertor/.sertor-version`, e la
  parte runtime di `.sertor/`) sono **dichiarati prodotti dall'install a runtime**, non versionati (coerente
  col confine dogfood: `.sertor/` runtime è gitignorato per design). Invece **`.sertor/sertor-cli-reference.md`**
  — che il dry-run ha visto **creato** dall'install e che è utile come reference — va **presente** nel dogfood
  (verificarne il tracking: se la sua dest è tracciata, committarlo; se gitignorata, dichiararlo). La regola:
  presenza-via-processo **o** assenza dichiarata con motivo (SC-5), zero asset la cui unica provenienza è lo
  script (SC-2).

## D8 — Sync/script: retrocessione a guardia, non fonte (DA-4 / FR-006 / REQ-010)

- **Decisione:** **retrocedere, non rimuovere** (REQ-010 è Could). `sertor_installer.sync` +
  `packages/sertor-flow/.../sync.py` + `materialize-speckit.ps1` restano come **dev-tool / guardia
  anti-drift**, ma **cessano di essere la "via di fedeltà"**: la documentazione (rituale post-merge in
  `CLAUDE.md`, header dei moduli sync, header dello script) va aggiornata perché **non indichi più il sync
  come modo di *ottenere* gli asset** — la fonte è il vero install. Le guardie byte restano attive e verdi.
- **Rationale:** rimuovere il sync ora eliminerebbe la rete anti-drift senza un rimpiazzo automatico
  (l'install manuale a ogni bump non è ancora meccanizzato); «guardia sì, fonte no» conserva la rete e
  chiude l'ambiguità sulla sorgente. La rimozione piena resta opzione futura (REQ-010, Could).

## D9 — `wiki/log.md` legacy (FR-008 / E15-FEAT-006, slice)

- **Fatto:** `init_structure` (in `sertor-core`, consumato da `install wiki`) crea `wiki/log.md`
  monolitico **non-distruttivo** (skip se esiste); la rotazione `wiki/log/<data>.md` richiede config e
  `migrate_log`. Il dogfood usa già la rotazione → l'install crea un `wiki/log.md` **spurio**.
- **Decisione (slice minima in ambito):** (a) **scartare** il `wiki/log.md` spurio dal dogfood (la
  conoscenza resta in `wiki/log/`); (b) **template/installer**: far sì che la struttura prodotta rispetti
  la rotazione **o** dichiarare il `wiki/log/` del dogfood come forma-client super-set preservata (REQ-005).
  La riscrittura completa della meccanica di rotazione lato template resta **E15-FEAT-006** proper.
- **Rationale:** US5 è P3, coordinata con FEAT-006, non blocca il cuore. Evitiamo lo scope-creep: risolviamo
  lo spurio nel dogfood (immediato) e promuoviamo il resto (backlog, non sepolto).

---

## Sintesi decisioni

| # | Tema | Decisione |
|---|------|-----------|
| D1 | Line-ending | LF ovunque (`.gitattributes` dogfood+bundle+template) + renormalize; FEAT-010 in ambito |
| D2 | CLAUDE.md lingua | bilingue (blocchi EN + prosa IT), accettato |
| D3 | Marker vs prosa | ibrido per-blocco (RAG tieni · WIKI prosa-vince · SDLC ibrido); tocca solo il dogfood |
| D4 | Ordine installer | flow → rag → wiki |
| D5 | Verifica | riuso guardie byte (su esito processo) + test idempotenza + test negativo EOL |
| D6 | FEAT-009 | non è dipendenza (chiusa not-a-bug) |
| D7 | Residui non-byte | presenza-via-processo o assenza dichiarata; `.sertor/` runtime gitignorato per design |
| D8 | Sync/script | retrocessi a guardia/dev-tool (non fonte); doc aggiornata; rimozione = futuro (Could) |
| D9 | wiki/log.md | scartato nel dogfood (slice); rotazione template completa = FEAT-006 |

Tutte le NEEDS CLARIFICATION risolte → si procede a Phase 1.
