# Epica — SpecLift (diff → requisiti EARS ancorati)

> **Origine:** handoff da **Sinthari** (`github.com/themetriost/Sinthari`, `master @ be4da28`, PR #5,
> MVP mergiato, 104 test verdi) — vedi `wiki/sources/input-other-agents/processed/speclift-handoff-sinthari.md`
> (richiesta integrale) e `wiki/sources/input-other-agents/speclift-recon.md` (ricognizione ancorata a
> `file:riga`, fonte primaria dei fatti tecnici citati qui).

## 1. Visione e problema (perché)

**SpecLift** è una capacità che, dato un **changeset git** (un commit, un range `A..B`, o il diff
*staged*), genera **requisiti EARS ancorati** su più livelli insieme (*multi-quota*: capacità utente /
comportamento / implementazione), ognuno legato a `file:righe` + simbolo + (se esiste) il test che
fallirebbe se il requisito si rompesse — è il ponte `diff → requisito`.

Il meccanismo dichiarato è un **"sandwich deterministico"**: una CLI a due marce fa il lavoro meccanico
e verificabile (`speclift bundle` estrae l'evidenza, `speclift assemble` la riverifica e la rende), e
**un solo stadio è intelligente** — l'agente chiamante, che legge il fascicolo di evidenza e scrive le
frasi EARS, mai un LLM interno alla CLI né un batch esterno. Ogni àncora citata dall'agente è poi
**riverificata sul filesystem** (il "moat") prima di essere accettata: ciò che non regge viene escluso
e segnalato, mai tenuto in silenzio.

**Perché a Sertor:** Sertor già fa *dogfooding* di se stesso (il RAG `sertor-rag` interroga il proprio
corpus). SpecLift è un'estensione naturale di questa pratica: usarlo sui **propri changeset** per
generare requisiti EARS ancorati e riconciliare `CLAUDE.md`/`requirements/`/wiki con l'implementazione
reale — è esattamente il lavoro che oggi il **punto 3 del rituale di step** ("lint semantico di
allineamento") chiede al flusso principale di fare **a mano**, confrontando claim del wiki con la
realtà del repo. SpecLift non sostituisce quel giudizio (resta all'agente, per costruzione — un solo
stadio intelligente), ma gli fornisce **evidenza ancorata e riverificata** invece di un confronto libero.

**Allineamento onesto alla missione (stella polare):** SpecLift **non tocca direttamente** il
differenziatore di Sertor (la fusione code+doc *resa al retrieval*) — non è un motore di retrieval, non
modifica `search_combined`/gli engine, non aggiunge una porta al core. È **periferico** al
differenziatore diretto, ma **rafforza la qualità e la veridicità del contesto nel tempo**: produce un
artefatto — requisiti ancorati e riverificabili — che tiene i documenti onesti rispetto al codice reale,
prevenendo esattamente il tipo di drift che il rituale di step già cerca di correggere manualmente. Va
dichiarato con onestà: il suo contributo alla missione è **indiretto** (qualità/freschezza del contesto
documentale che il RAG poi serve), non diretto (non migliora hit-rate/MRR/fusion coverage).

**Cosa chiede l'handoff, letteralmente (due cose, il *come* è nostro):**
1. **Self-hosting/dogfooding** — rendere SpecLift utilizzabile nel repo Sertor.
2. **Distribuzione via installer** — renderlo disponibile a un ospite che installa Sertor, sulla
   falsariga delle skill già distribuite (`requirements`, `speckit-*`).

## 2. Ambito

### In ambito
- **Self-hosting/dogfooding di SpecLift su Sertor** (FEAT-001, decomposta in
  [`requirements/speclift/self-host/requirements.md`](self-host/requirements.md)).
- **Distribuzione di SpecLift via installer** su un ospite terzo (FEAT-002) — la **casa di
  distribuzione non è decisa qui**: è una tensione dichiarata (§5), da risolvere nella fase
  specify/plan di quella feature.
- **Tracciamento** (non implementazione) della famiglia futura di capacità a valle dello stesso
  primitivo `diff→requisito` (SpecAudit, Debrief, Guida al test) come voci di backlog Could/futuro.

### Fuori ambito
- **Decidere ora** la casa di distribuzione di FEAT-002 (rinviato).
- **Implementare** SpecAudit / Debrief / Guida al test: sono capacità distinte e future, non
  decomposte da questa epica (l'handoff le elenca esplicitamente come "fuori scope", §7).
- **Qualunque modifica a `sertor_core`** (Principio XI): SpecLift consuma il retrieval di Sertor
  **esclusivamente** tramite il vehicle CLI `sertor-rag search`, mai importando la libreria.
- **Traduzione IT→EN** degli asset SpecLift (codice/commenti/skill sono in italiano) — tema
  linguistico trasversale del prodotto, tracciato altrove; non in ambito qui.
- **Contribuire a monte a Sinthari** (aprire PR sul loro repo): fuori dal perimetro di questa epica,
  che riguarda solo il lato Sertor della relazione.

## 3. Criteri di successo

- **CS-1 (self-host funzionante):** `speclift bundle <ref>` eseguito su un commit reale del repo
  Sertor produce un fascicolo di evidenza non vuoto con àncore su file Sertor reali; `speclift
  assemble` produce un report canonico (JSON+Markdown) le cui àncore sono verificate sul filesystem di
  Sertor. Verificabile eseguendo il ciclo completo su un commit dogfood.
- **CS-2 (Principio XI intatto):** `sertor_core` risulta **invariato** (zero modifica, zero nuovo
  import) come conseguenza del vendoring/self-hosting. Verificabile con `git diff` sul pacchetto core
  e con l'assenza di `import sertor_core`/`from sertor_core` in `packages/speclift`.
- **CS-3 (nessun ciclo di dipendenze):** il nuovo membro del workspace non introduce un ciclo di
  dipendenze tra i pacchetti (`sertor-core` ↔ `sertor` ↔ `sertor-install-kit` ↔ `sertor-flow` ↔
  `speclift`). Verificabile con `uv sync --all-packages` senza errori di risoluzione.
- **CS-4 (distribuibile su almeno un ospite):** dopo la decisione di casa (FEAT-002), un ospite che
  installa Sertor riceve SpecLift funzionante (skill + CLI eseguibile), non solo il testo della skill.
- **CS-5 (valore dichiarato per il rituale, non enforcement):** SpecLift è **utilizzabile** come
  strumento di supporto al lint semantico del rituale di step, ma **non sostituisce** il giudizio
  dell'agente né diventa un gate automatico — la sua adozione nel rituale resta una scelta esplicita,
  non imposta da questa epica.

## 4. Stakeholder e attori

- **Sinthari** — mittente dell'handoff, manutentore upstream del codice SpecLift; non ha (ancora)
  analizzato la struttura di `packages/sertor-flow` di Sertor (verificato: nessun documento di
  ricognizione lato loro), quindi la decisione di packaging è interamente nostra.
- **Manutentore di Sertor** — owner del workspace, garante del Principio XI (isolamento del core) e
  dell'assenza di cicli di dipendenza; decide la casa di distribuzione in FEAT-002.
- **Agente frontier dell'ospite** (Claude/Copilot) — è lo **stadio di giudizio** del sandwich: legge il
  fascicolo di evidenza e scrive le frasi EARS tramite la skill `speclift`.
- **Contributore/manutentore che legge i requisiti prodotti** — beneficiario finale: requisiti
  affidabili perché ancorati e riverificati, non narrativa libera.

## 5. Vincoli, assunzioni e dipendenze

**Vincoli di design ereditati dall'handoff (§5, "decisioni prese, non da rimettere in discussione" —
si applicano a SpecLift e a ogni capacità futura della stessa famiglia, non solo a FEAT-001):**
- **Sandwich deterministico:** CLI meccanica e verificabile; **un solo** stadio intelligente = l'agente
  chiamante che scrive le frasi EARS (mai un batch esterno o un LLM interno alla CLI).
- **Il "moat":** ogni àncora (file:righe + simbolo + test) è riverificata sul filesystem dopo la
  stesura; ciò che non regge viene scartato ed è **sempre** segnalato, mai accettato in silenzio.
- **Multi-quota sempre:** capacità utente / comportamento / implementazione generati insieme.
- **Filtro sorgenti:** `specs/`, `requirements/`, `.specify/` sempre esclusi (circolarità); config
  inclusa; documentazione opzionale via `--include-docs`.
- **Localizzazione solo via il vehicle CLI/MCP di Sertor** — mai `import sertor_core` a mano (stesso
  Principio XI che Sertor applica a se stesso).
- **Fail-loud:** ref invalido, RAG giù, bundle invalido → errore esplicito con exit code dedicato, mai
  fallback silenzioso.
- **Corpo skill host-agnostico:** nessun path d'assistente né slash-command hardcoded.

**Fatti verificati dal recon (`speclift-recon.md`), rilevanti a livello di epica:**
- Il pacchetto `speclift` è **self-contained** sotto `src/speclift/`, hatchling, dominio puro
  ports&adapters, **zero import di `sertor_core`** — vendorabile come membro del workspace senza
  dipendere dal core, sulla falsariga di `sertor-flow`.
- La dipendenza dal RAG di Sertor è **un solo comando CLI**: `sertor-rag search <q> --type code --json
  -k 5` via subprocess (`adapters/rag_sertor.py:86`), non il code-graph MCP
  (`find_symbol`/`who_calls`) che l'handoff e la wiki Sinthari citano — **discrepanza doc↔codice**
  dichiarata (vedi Rischi).
- Il vehicle è **hardcodato** come default di un campo `Config`
  (`("uv","run","--project",".sertor","sertor-rag")`, `config.py:27`); nel repo Sertor il RAG vive a
  **root** (`uv run sertor-rag`), non in un sottoprogetto `.sertor/`.
- `requires-python = ">=3.12"` (Sinthari) contro `>=3.11` su **tutti** i pacchetti Sertor; nessuna
  sintassi 3.12-only rilevata nel grep (`StrEnum` è 3.11+) — il pin è **probabilmente riducibile**, da
  verificare con la suite reale.
- Unica dipendenza runtime dichiarata: `jsonschema` (usata solo dai test di contratto).

**Dipendenze:**
- L'indice RAG del repo ospite dev'essere **costruito e fresco**: SpecLift **consuma** l'indice
  (non lo costruisce). Su Sertor questo prerequisito è già coperto dal rituale/hook di freschezza
  esistenti (`sertor-rag index .`, hook `rag-freshness`, E10-FEAT-011/016).
- La distribuzione (FEAT-002) dipende dalla decisione di casa (sertor-flow vs pacchetto `sertor` vs
  standalone), non presa in questa epica.

**Assunzione:** l'MVP di Sinthari è stabile (mergiato, 104 test verdi) e non subirà modifiche upstream
imminenti che invaliderebbero il vendoring nel breve periodo.

## 6. Rischi

- **R-1 — Discrepanza doc↔codice sul legame RAG:** l'handoff e la wiki Sinthari affermano che SpecLift
  usa il code-graph MCP (`find_symbol`/`who_calls`); il codice usa **solo** `sertor-rag search --type
  code --json`. Chi legge solo la narrativa si aspetta un'integrazione più profonda di quanto esista.
  **Mitigazione:** dichiararlo esplicitamente in ogni documento derivato (già fatto in questa epica e
  nella decomposizione FEAT-001).
- **R-2 — Tensione versione Python:** se il pin `>=3.12` risultasse davvero irriducibile (contro
  l'evidenza attuale), un membro del workspace più stretto alzerebbe il pavimento effettivo dell'intero
  `.venv` `uv` a 3.12. **Mitigazione:** verifica empirica (far girare la suite su 3.11) prima di
  accettare il vendoring; se irriducibile, dichiararlo e valutare risoluzione/distribuzione separata.
- **R-3 — Casa di distribuzione indecisa (FEAT-002):** tensione reale tra "`sertor-flow` è per
  costruzione ortogonale al RAG" (nessuna dipendenza da `sertor-core`/dal RAG) e "SpecLift richiede il
  RAG a runtime". L'invariante di pacchetto ("nessun import `sertor_core`") si preserva comunque
  (SpecLift consuma via vehicle subprocess, non import), ma la **dipendenza funzionale runtime** dal
  RAG resta un prerequisito che `sertor-flow` oggi non ha mai avuto verso nessuna delle sue skill.
  **Non risolto qui** — decisione rinviata a FEAT-002.
- **R-4 — Precedente architetturale:** SpecLift è, per quanto verificato, la **prima skill del flow con
  una CLI runtime propria** (le skill esistenti — `requirements`, `speckit-*` — sono asset puri, solo
  istruzioni). Questo apre un precedente che va gestito con cura (packaging, versionamento,
  manutenzione) per non aprire la porta a una proliferazione incontrollata di CLI-in-skill.
- **R-5 — Deriva silenziosa del vendoring:** se SpecLift è vendorato come copia (non sincronizzata
  automaticamente), il codice può divergere silenziosamente dall'upstream Sinthari nel tempo.
  **Mitigazione:** nota di provenienza esplicita (repo, commit, versione) — vedi FEAT-001, DA-1.

## 7. Requisiti trasversali (EARS)

Pochi, veramente validi per l'intera epica (ogni feature a valle li eredita):

- **REQ-E1 (Ubiquitous):** *The speclift capability shall never import `sertor_core` directly; it
  shall interact with Sertor's retrieval exclusively through Sertor's supported agent-facing vehicle
  — the `sertor-rag` **MCP server** (encapsulated in a skill), not the `sertor-rag` CLI — consistent
  with Principio XI and with Sertor's rule that external consumers integrate via the MCP (the CLI is a
  thin/internal consumer). Historical note: the upstream Sinthari code uses the CLI vehicle; the CLI→MCP
  divergence is intentional and has been fed back to Sinthari (see FEAT-001 self-host, Gruppo H).*
- **REQ-E2 (Unwanted):** *If the Sertor RAG index is missing or unreachable, then speclift shall fail
  loud with an explicit, actionable error and a dedicated exit code, never degrading silently or
  fabricating anchored requirements.*
- **REQ-E3 (Ubiquitous):** *The judgment stage of speclift (authoring EARS statements from evidence)
  shall always be performed by the calling agent, never by an in-process LLM call or an external batch
  process.*
- **REQ-E4 (Ubiquitous):** *Every anchor cited in a speclift-generated requirement shall be
  re-verified against the real filesystem before being rendered in the final report; anchors that do
  not verify shall be excluded and reported, never silently kept.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|--------------------|-------|
| FEAT-001 | **Self-hosting/dogfooding su Sertor** — vendoring come nuovo membro del workspace, riconciliazione versione Python, vehicle RAG configurato per Sertor, skill depositata per il dogfood, fail-loud sul prerequisito RAG, test integrati, verifica end-to-end su un commit reale | Sertor genera requisiti EARS ancorati dai propri changeset reali; primo passo prima di distribuire a chiunque altro | **Must** | ✅ **consegnata su `master`** — vedi EXEC (E14, merge `bbfb74d`/PR #136). Requisiti: [`self-host/requirements.md`](self-host/requirements.md) |
| FEAT-002 | **Distribuzione via installer** — rendere SpecLift installabile su un ospite esterno che installa Sertor; la casa di distribuzione (sertor-flow con prereq RAG dichiarato / pacchetto `sertor` / pacchetto standalone) **non è decisa** | Un ospite riceve SpecLift funzionante (skill + CLI), non solo un pezzo di testo | **Should** | da decomporre — decisione di casa aperta (vedi §5 R-3); rinviata alla fase specify/plan di questa feature |
| FEAT-003 | **SpecAudit** — verdetto **per requisito** (SODDISFATTO / PARZIALE / MANCANTE / DRIFTED / NON_DOCUMENTATO, con confidenza e **citazione dell'àncora SpecLift**) confrontando i requisiti originali (`requirements/`) con l'output ancorato di SpecLift per lo stesso changeset. Back-translation top-down del gate pre-merge; **non legge mai codice/test/CI**, moat **strutturale** (completezza/integrità dei riferimenti/citazione senza riverifica, fail-loud) | Chiude il loop lint-semantico con uno strumento dedicato invece del confronto manuale | **Should** (era Could) | 🔄 **self-host/dogfood vendorato ✅ (2026-07-02)** — vendorato verbatim in **`packages/specaudit`** (stampo SpecLift: membro workspace `uv`, `VENDORING.md`, LICENSE MIT, pin Sinthari `e1bbdb2`; **59 test verdi** su 3.11+3.12, ruff pulito, step CI per-pacchetto), skill in `.claude/skills/specaudit/` per il dogfood. Consuma `*.speclift.json` → prerequisito SpecLift self-hosted (FEAT-001 ✅) **soddisfatto**. Anticipato per testare la coppia SpecLift→SpecAudit sui changeset delle A. **Resta:** distribuzione su ospiti esterni (separata, gemella di FEAT-002). Handoff in `processed/` |
| FEAT-004 | **Debrief** — consumatore a valle dello stesso primitivo `diff→requisito`: genera un resoconto/riassunto di sessione o PR ancorato all'evidenza | Riassunti di lavoro affidabili, non narrativa libera | **Could** | non decomposta — capacità futura (handoff §7) |
| FEAT-005 | **Guida al test** — consumatore a valle: genera indicazioni/casi di test a partire dai requisiti ancorati e dai test già collegati alle àncore | Meno lavoro manuale nel derivare test da un requisito ancorato | **Could** | non decomposta — capacità futura (handoff §7) |

> **Nota sul phasing:** FEAT-003/004/005 sono **elencate, non decomposte**: sono consumatori a valle
> dello stesso primitivo che FEAT-001/002 rendono disponibile, ma restano capacità distinte e future
> (l'handoff stesso le tiene fuori scope, §7). Decomporle richiederebbe prima che FEAT-001 (e
> idealmente FEAT-002) siano consegnate.

## 9. Domande aperte

- **[DA CHIARIRE in FEAT-002 — specify/plan]** Casa di distribuzione di SpecLift: `sertor-flow` (con
  un prerequisito RAG dichiarato esplicitamente, che romperebbe per la prima volta la sua ortogonalità
  storica rispetto al RAG) **vs** pacchetto `sertor` (coerente perché già RAG-coupled, ma SpecLift è
  SDLC/governance non retrieval) **vs** pacchetto standalone installabile a sé (nessuna delle due
  tensioni, ma un terzo installer da mantenere). Non decisa in questa epica.
- **[DA CHIARIRE in FEAT-001 — plan]** Vedi le tre decisioni aperte nella decomposizione
  ([`self-host/requirements.md`](self-host/requirements.md) §10): copia versionata vs sync dal repo
  Sinthari; `jsonschema` runtime vs dev; meccanismo di configurazione del vehicle RAG per il self-host
  vs un futuro ospite generico.
- **[Nota di processo, non un DA]** L'assegnazione di un numero d'epica nella vista standing
  `E1`..`E13` (`wiki/syntheses/roadmap.md`) e l'eventuale voce in *Nuove funzionalità da discutere*
  sono bookkeeping del rituale di step (distill/registrazione), non di questo artefatto di requisiti.
