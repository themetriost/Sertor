---
title: Roadmap & stato di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-07-30
sources: ["requirements/**/epic.md", "specs/**", ".specify/memory/constitution.md", "VERSION", "CHANGELOG.md"]
---

# Roadmap & stato — Sertor

> **Pagina viva: solo lo stato di OGGI.** Dove siamo e cosa fare adesso. La cronologia delle consegne e
> il racconto delle feature già chiuse vivono in **[[storico-roadmap]]** — separati il 2026-07-30, quando
> questa pagina aveva raggiunto 717 righe di cui la maggior parte storia. *Una pagina che si legge per
> sapere «cosa faccio ora» non può chiedere di scorrere sei mesi di consegne per scoprirlo.*
>
> **Stato verificato contro i sorgenti il 2026-07-30**, non riportato a memoria: 227 righe di backlog
> lette dai 16 `epic.md`, 36 hash di consegna verificati come antenati di `master`, artefatti controllati
> per esistenza. I drift trovati sono stati corretti nello stesso passaggio (vedi *Come è stato
> verificato* in fondo).

<!-- EXEC:START -->
## ⚡ Executive summary (stato al 2026-07-30)

**Versione pubblicata: `v0.4.0`** · `master` = `f3e2a31` · CI verde · **nessuna PR aperta**.
Rilascio **notificato**: GitHub Release *latest* · bacheca (canale *Releases*) · auto-updater degli
ospiti, **sveglio dal bump** (era dormiente-fino-alla-release per costruzione).

### 🔄 In progress

**Niente in corso.** L'ultima consegna è **E15-FEAT-012** (smoke di aggiornamento, merge `eeca79e`/PR
#256), rilasciata in **v0.4.0** insieme ai tre fix nati dai riscontri del nodo *Acta* del 29/07. Il
flusso è **fermo alla scelta della prossima direzione** (vedi *Prossime direzioni*).

**🎯 Il numero che orienta la scelta: dei 110 item aperti, i Must sono TRE** — e tutti e tre stanno in
epiche **differite** (E11 `multiutente`) o **non iniziate** (E9 `second-brain`). Il resto è **48 Should
e 58 Could**. Cioè: **nessun Must aperto nelle epiche attive**. La domanda non è più «cosa manca perché
sia completo», è «quale direzione vogliamo» — e va posta all'utente, non dedotta dal backlog.

**Il fatto nuovo che cambia come rilasciamo:** da oggi un rilascio parte solo dopo aver verificato, su
host usa-e-getta, che un **`upgrade`** lo consegna davvero. Prima lo si deduceva dal merge — ed è il
motivo per cui **13 difetti su 14** arrivavano dal campo invece che dai nostri test: tutti e 7 quelli
d'installer richiedono un'installazione **preesistente più vecchia** per manifestarsi, e nemmeno il
dogfood aggiorna (il suo runtime insegue HEAD). Misura corrente: `v0.3.0 → master` verde su **4
combinazioni**, 8 esiti su 8.

### 📊 Copertura per epica (verificata sui sorgenti)

| # | Epica | Consegnate | Aperte | Copertura | Stato |
|---|---|---|---|---|---|
| **E1** | [`sertor-core`](../../requirements/sertor-core/epic.md) | 10/10 | 0 | 100% | ✅ **completa** *(1 promossa altrove)* |
| **E2** | [`sertor-cli`](../../requirements/sertor-cli/epic.md) | 18/25 | 7 | 72% | 🔄 in corso *(1 ritirata)* |
| **E3** | [`osservabilita`](../../requirements/osservabilita/epic.md) | 8/16 | 8 | 50% | 🔄 in corso |
| **E4** | [`memoria-conversazioni`](../../requirements/memoria-conversazioni/epic.md) | 11/15 | 4 | 73% | 🔄 in corso |
| **E5** | [`retrieval-qualita`](../../requirements/retrieval-qualita/epic.md) | 6/13 | 7 | 46% | 🔄 in corso |
| **E6** | [`backend-store-scala`](../../requirements/backend-store-scala/epic.md) | 0/7 | 7 | 0% | 📋 non iniziata |
| **E7** | [`ingestione-estesa`](../../requirements/ingestione-estesa/epic.md) | 0/4 | 4 | 0% | 📋 non iniziata |
| **E8** | [`conoscenza-schema-sql`](../../requirements/conoscenza-schema-sql/epic.md) | 0/3 | 3 | 0% | 📋 non iniziata |
| **E9** | [`second-brain`](../../requirements/second-brain/epic.md) | 0/10 | 10 | 0% | 📋 non iniziata |
| **E10** | [`debito-tecnico`](../../requirements/debito-tecnico/epic.md) | 39/65 | 26 | 60% | 🔄 in corso |
| **E11** | [`multiutente`](../../requirements/multiutente/epic.md) | 0/6 | 6 | 0% | 📋 non iniziata |
| **E12** | [`usabilita`](../../requirements/usabilita/epic.md) | 5/14 | 9 | 36% | 🔄 in corso |
| **E13** | [`documentazione-marketing`](../../requirements/documentazione-marketing/epic.md) | 8/15 | 7 | 53% | 🔄 in corso |
| **E14** | [`speclift`](../../requirements/speclift/epic.md) | 2/5 | 3 | 40% | 🔄 in corso |
| **E15** | [`fedelta-dogfood`](../../requirements/fedelta-dogfood/epic.md) | 7/12 | 5 | 58% | 🔄 in corso *(1 ritirata)* |
| **E16** | [`evoluzione-modello-wiki`](../../requirements/evoluzione-modello-wiki/epic.md) | 0/4 | 4 | 0% | 📋 non iniziata |
| | **TOTALE** | **114/224** | **110** | **51%** | — |

> **Come leggere «Consegnate»:** il denominatore esclude le feature **ritirate** (`❌ Won't`/not-a-bug) e
> quelle **promosse ad altra epica** — contarle come debito gonfierebbe il residuo con lavoro che nessuno
> deve fare. E1 risulta completa proprio così: la sua unica voce non consegnata è migrata a E7.

### 📋 Prossime direzioni (da scegliere)

1. **E2-FEAT-023** — `upgrade` nudo copre una capability sola uscendo verde. È **il settimo difetto** che
   il gate d'aggiornamento non copre, dichiarato fuori copertura perché aperto: chiuderlo porta SC-001 a
   **7/7** e toglie l'unica deroga. *Il candidato naturale.*
2. **Coda dei riscontri dal campo, ancora aperta** — E10-FEAT-060 (`ritual-check` e `wiki-guard` misurano
   realtà diverse, usato da *Acta* come prova) · E10-FEAT-063 (`packages/` e `CLAUDE.md` **fuori** dal
   perimetro di `scan`: il gate non guarda la superficie che arriva agli ospiti) · E10-FEAT-047
   (`wiki/log/index.md` duplica un fatto derivabile) · E10-FEAT-049 + E13-FEAT-014 (riferimenti entranti /
   anti-drift della doc utente — **stessa forma, da progettare insieme**).
3. **Chiudere E4** (73%) — restano 3 Could: remember-this · retention · ponte second-brain.
4. **E14 — distribuire SpecLift/SpecAudit agli ospiti** (FEAT-002, casa `sertor-flow`): 3.916 righe di
   codice **non installabili da nessuno**, che è la definizione di feature non completa. *Decisione
   sospesa: usare · congelare · ritirare.*
5. **E13 Fase 2 — marketing** (posizionamento/demo/landing), sbloccata dal go-public.
6. **E15-FEAT-014** — matrice esaustiva «da ogni versione all'ultima»: ora **parzialmente risposta**
   (4 combinazioni, 4 release indietro).
7. **Scommesse grandi** — E7 ingestione → **sblocca E8** · E6 PGVector · E9 second-brain · E5 leve
   retrieval residue (**solo** con lift misurato).

**Fermi per decisione utente:** go-public/PyPI (E2-FEAT-006, dal 2026-07-17) · E11 `multiutente`
(differita) · E2-FEAT-019 (attesa esterna Noetix) · migrazione ad **Acta v0.5.0** (il rimedio al residuo
`acta` machine-wide tocca gli altri nodi dell'host).

> **⚠️ La superficie che nessuna guardia presidia — emersa il 2026-07-30, da rifletterci prima di
> scegliere.** In un giorno si sono rotte **due** superfici testuali: la roadmap (5 voci che dichiaravano
> uno stato falso) e le **note di rilascio** (comandi non eseguibili, pubblicati su tre canali). Nessuna
> delle due ha un test. Il codice ha le suite, gli asset la parità, i blocchi distribuiti il budget di
> righe — *ciò che raccontiamo non ha nulla*. E in entrambi i casi il difetto è stato colto da una
> **domanda dell'utente**, non da una nostra rilettura. Le due contromisure tracciate — **E13-FEAT-014**
> (anti-drift della doc utente) e **E10-FEAT-049** (riferimenti entranti) — coprono metà del problema:
> **nessuna delle due guarda le note di rilascio**.

<!-- EXEC:END -->

---

## 📖 Le voci aperte, per epica

> Censimento **completo** di ciò che resta, derivato dai `epic.md` il 2026-07-30. 🔄 = iniziata · 📋 = da
> fare. Il dettaglio (valore, vincoli, origine) sta nella riga dell'epica: qui c'è l'elenco, non la sostituzione.


**E2 · [`sertor-cli`](../../requirements/sertor-cli/epic.md)** — 7 aperte

- 🔄 **E2-FEAT-006** — Distribuzione pubblica su PyPI (versioning pubblico, licenza, hardening supply-chain) · *~~Won't~~ → **Should (*
- 📋 **E2-FEAT-019** — Granularità del bundle sertor-flow: asset selezionabili + blocco CLAUDE.md opzionale — oggi sertor-flow i · ***Should (P1)***
- 📋 **E2-FEAT-020** — Log ispezionabile install.event/1 per wiki/governance + upgrade/uninstall — E2-FEAT-018 ha consegnato il  · ***Should***
- 📋 **E2-FEAT-023** — sertor upgrade nudo non copre le capability installate, e non lo dichiara — sul nodo Kaelen sertor upgrad · ***Should***
- 📋 **E2-FEAT-024** — Minori d'installazione emersi dal campo — tre attriti piccoli e indipendenti, raccolti insieme: (a) .clau · ***Could***
- 📋 **E2-FEAT-025** — Un install che fallisce a metà deve dichiarare in che stato lascia l'ospite — execute_plan è fail-fast se · ***Should***
- 📋 **E2-FEAT-026** — Il campo Version della costituzione porta DUE fatti — difetto programmato — per sertor-flow è la release  · ***Should (P1)***

**E3 · [`osservabilita`](../../requirements/osservabilita/epic.md)** — 8 aperte

- 📋 **E3-FEAT-006** — Metriche aggregate esposte (es. latenza p95/p99, cache-hit rate, throughput). Assorbe REQ-H10 dell'harden · ***Should***
- 📋 **E3-FEAT-007** — Stima costi in € — converte i token in una stima di spesa per provider (tabella prezzi in config aggiorna · ***Should** *(alzata da*
- 📋 **E3-FEAT-008** — Web mode — dashboard servita in locale nel browser, sopra lo stesso strato di osservabilità · ***Could***
- 📋 **E3-FEAT-009** — Trend di qualità del retrieval — andamento di low_confidence (astensioni), query a vuoto, distribuzione d · ***Could***
- 📋 **E3-FEAT-010** — Metriche del code-graph e del wiki — #nodi/#archi e copertura per linguaggio; #pagine, orfani/link rotti, · ***Could***
- 📋 **E3-FEAT-011** — Export report CSV/MD + bucket temporale «hour» — esportazione dei report (oltre la TUI) e granularità ora · ***Could***
- 📋 **E3-FEAT-012** — Rilevamento del drift dell'indice — check che confrontano lo stato reale della sorgente con l'indice/mani · ***Should***
- 📋 **E3-FEAT-016** — Visibilità degli esiti di valutazione (TUI + OTel) — (a) scheda "Eval" nella TUI che rende l'ultimo eval/ · ***Should***

**E4 · [`memoria-conversazioni`](../../requirements/memoria-conversazioni/epic.md)** — 4 aperte

- 📋 **E4-FEAT-005** — Cattura selettiva "remember this" — marcatura esplicita di cosa archiviare, invece di tutto · ***Could***
- 📋 **E4-FEAT-006** — Governance/retention del contenuto — politiche di scadenza, scrub configurabile, cancellazione selettiva · ***Could***
- 📋 **E4-FEAT-007** — Ponte verso il second-brain — formato/superficie compatibili con la promozione cross-progetto · ***Could***
- 📋 **E4-FEAT-015** — Continuità di sessione: al riavvio, iniettare nel contesto gli ultimi turni di conversazione (richiesta u · ***⚠️ DA ELICITARE***

**E5 · [`retrieval-qualita`](../../requirements/retrieval-qualita/epic.md)** — 7 aperte

- 📋 **E5-FEAT-002** — Eval comparativa live su provider reale (REQ-051, marker cloud) — confronto motori/provider col modello f · ***Could** *(abbassata *
- 📋 **E5-FEAT-004** — Calibrazione delle soglie di pertinenza — derivare SERTOR_MIN_SCORE e affini dal ground-truth · ***Should***
- 📋 **E5-FEAT-005** — Query transformation (multi-query / HyDE) — riformulazione/espansione della query (opt-in) [ex REQ-H7] · ***Could***
- 📋 **E5-FEAT-006** — Filtro per metadata esteso — restrizione del retrieval per attributi (path/linguaggio/doc_type…) [ex REQ- · ***Could***
- 📋 **E5-FEAT-007** — Contextual retrieval (Anthropic) — arricchimento del chunk con contesto di documento prima dell'embedding · ***Could***
- 📋 **E5-FEAT-010** — Pavimento assoluto di qualità — soglia minima assoluta opzionale (es. SERTOR_EVAL_MIN_MRR/hit) come gate  · ***Could***
- 📋 **E5-FEAT-013** — Harness di valutazione agent-facing — misura l'effetto della forma di un risultato sulla risposta dell'ag · ***Should***

**E6 · [`backend-store-scala`](../../requirements/backend-store-scala/epic.md)** — 7 aperte

- 📋 **E6-FEAT-001** — Adapter VectorStore PGVector (Azure) dietro la porta esistente · ***Should***
- 📋 **E6-FEAT-002** — Adapter VectorStore MongoDB / Atlas (Azure) (vector + eventuale Atlas Search ibrido) · ***Could***
- 📋 **E6-FEAT-003** — Indici multi-provider in parallelo — collezioni con embedder/dimensioni diverse coesistenti, interrogabil · ***Could***
- 📋 **E6-FEAT-004** — Query federata su >2 corpora / fan-out a N collezioni — estende la feature 010 (fail-fast su provider ete · ***Could***
- 📋 **E6-FEAT-005** — search_docs esteso al fan-out + dedup cross-collezione v2 · ***Could***
- 📋 **E6-FEAT-006** — Scala del code-graph oltre l'in-memory — backend a grafo persistente (Neo4j opzionale) oltre la soglia ~5 · ***Could***
- 📋 **E6-FEAT-007** — Azure AI Search: dichiarare experimental o testare — la traccia store cloud odierna (store_backend=azure) · ***Should***

**E7 · [`ingestione-estesa`](../../requirements/ingestione-estesa/epic.md)** — 4 aperte

- 📋 **E7-FEAT-001** — Repository remoti via URL — clone/fetch come sorgente del corpus · ***Could***
- 📋 **E7-FEAT-002** — Formati non-testo (PDF/DOCX/notebook → testo) nell'ingestione documentale · ***Could***
- 📋 **E7-FEAT-003** — Chunking sintattico esteso — PowerShell / T-SQL / PL-SQL / Bash da fallback a tree-sitter · ***Could***
- 📋 **E7-FEAT-004** — No-code-first — wiki/RAG su progetti senza codice (solo doc) · ***Could***

**E8 · [`conoscenza-schema-sql`](../../requirements/conoscenza-schema-sql/epic.md)** — 3 aperte

- 📋 **E8-FEAT-001** — Ingestione della conoscenza-schema nel corpus unico — DDL/FK, viste, SP, query «buone» con doc_type dedic · ***Should***
- 📋 **E8-FEAT-002** — Schema-graph parallelo al code-graph — entità+relazioni tabella↔vista↔SP↔query, navigazione tipo who_call · ***Could***
- 📋 **E8-FEAT-003** — Fusione schema ↔ codice applicativo — collega l'accesso al DB nel codice alle entità schema · ***Could***

**E9 · [`second-brain`](../../requirements/second-brain/epic.md)** — 10 aperte

- 📋 **E9-FEAT-001** — Catalogo / meta-roadmap di flotta — vista trasversale auto-assemblata dai blocchi EXEC dei progetti · ***Must***
- 📋 **E9-FEAT-002** — Query federata cross-progetto + escalation — interroga L2, poi fan-out sui corpora (riusa feature 010) · ***Should***
- 📋 **E9-FEAT-003** — Harvest & promote — distillazione cross-progetto (raccolta meccanica + promozione a giudizio, de-contestu · ***Should***
- 📋 **E9-FEAT-004** — Trust al meta-livello — confidence, corroborazione, decay, validità temporale, supersession · ***Should***
- 📋 **E9-FEAT-005** — Seed & apply — bootstrap di un progetto nuovo dalla saggezza accumulata · ***Could***
- 📋 **E9-FEAT-006** — Asset registry — catalogo versionato di skill/agent/hook con provenance, «dove è usato», propagazione upd · ***Could***
- 📋 **E9-FEAT-007** — Verifica & sicurezza degli asset — test che viaggia con l'asset + parametrizzazione (intento↔binding) + g · ***Could***
- 📋 **E9-FEAT-008** — Cross-project lint / drift — lint semantico a livello di flotta (una lesson regge ancora? chi diverge da  · ***Could***
- 📋 **E9-FEAT-009** — Codifica di metodologie / sintesi N→1 — pattern ricorrente su N progetti → asset nuovo (clustering varian · ***Could***
- 📋 **E9-FEAT-010** — Meta-grafo dei concetti/asset — relazioni tipate (generalizes/refines/contradicts/applies-when); porta so · ***Could***

**E10 · [`debito-tecnico`](../../requirements/debito-tecnico/epic.md)** — 26 aperte

- 📋 **E10-FEAT-004** — Rituale/governance come plugin portabile repo-agnostico (oltre ciò che sertor-flow copre) · ***Could***
- 📋 **E10-FEAT-005** — Igiene del wiki — hub/overview per-area, tassonomia più fine, distill pagina osservabilità, ripasso [[tre · ***Could***
- 📋 **E10-FEAT-006** — Robustezza del bundle sertor-flow — selettività (vs all-or-nothing) + hook harness governance (DA-g) · ***Could***
- 📋 **E10-FEAT-007** — Allineamento naming --assistant — unificare i due valori Copilot (copilot VS Code + copilot-cli) in un so · ***Could***
- 📋 **E10-FEAT-008** — Visibilità del context-load SessionStart su Copilot CLI — investigare se si può ridurre/eliminare la visi · ***Could***
- 📋 **E10-FEAT-014** — Robustezza invocazione manuale dell'hook freschezza (stdin non-bloccante) — lo script rag-freshness.ps1 ( · ***Could***
- 📋 **E10-FEAT-015** — Il refresh/upgrade non disinstalla bene gli artefatti obsoleti — il percorso di refresh (re-install via u · ***Could***
- 📋 **E10-FEAT-042** — upgrade --dry-run non proietta i SETTINGS_MERGE/CONFIG — in install_wiki.py (ramo UPGRADE) il dry-run rit · ***Should***
- 📋 **E10-FEAT-043** — Il breadcrumb .last-hook-error non viene mai riconciliato al ritorno in verde — l'artefatto fail-loud di  · ***Should***
- 📋 **E10-FEAT-044** — Lo skew di versione spegne in SILENZIO proprio gli aiuti «il tool trova, tu giudichi» — su un runtime rim · ***Should***
- 📋 **E10-FEAT-046** — upsert-index: riga in coda alla sezione sbagliata + wikilink in forma di path — la riga nuova finisce in  · ***Could***
- 📋 **E10-FEAT-047** — lint non rileva una partizione di log non elencata nell'indice — append-log crea la partizione del giorno · ***Could***
- 📋 **E10-FEAT-049** — Il lint semantico deve includere i riferimenti ENTRANTI della pagina toccata — contromisura sul come si e · ***Should***
- 📋 **E10-FEAT-050** — Le note della v0.2.1 presentano come UNIVERSALE un difetto che è condizionale — abbiamo pubblicato che l' · ***Should (P1)***
- 📋 **E10-FEAT-051** — Chiudere il gate wiki con un «giudizio registrato», non solo scrivendo — oggi wiki-guard è binario: l'uni · ***Could — da RIVALUTAR*
- 📋 **E10-FEAT-052** — La cache degli embedding conserva float64 dove lo store usa float32: metà dello spazio è precisione butta · ***Could (P2)***
- 📋 **E10-FEAT-053** — Codice morto: 3 shim di retrocompatibilità e i loro 13 test (~170 righe) — sertor_installer/{env_merge,gi · ***Could (P2)***
- 📋 **E10-FEAT-054** — Codice morto: specaudit/observability.py intero (27 righe), e dichiara il contrario — zero riferimenti ne · ***Should (P1)***
- 📋 **E10-FEAT-055** — Codice morto: i 3 formattatori «regression» di cli/output.py (~110 righe) — format_regression_report (451 · ***Could (P2)***
- 📋 **E10-FEAT-056** — Codice morto: 13 simboli tenuti in vita solo dai propri test — definiti in produzione, zero riferimenti i · ***Could (P2)***
- 📋 **E10-FEAT-057** — Superficie obsoleta (non morta): l'operazione sertor-wiki-tools migrate — è la migrazione una-tantum dal  · ***Could (P2)***
- 📋 **E10-FEAT-058** — Il lint applica al contenuto archiviato una regola pensata per quello vivo — dopo la riparazione dei 40 r · ***Should (P1)***
- 📋 **E10-FEAT-059** — Regola del boy scout: se il lint trova rotto, si aggiusta nello stesso passaggio — direttiva utente (2026 · ***Should (P1)***
- 📋 **E10-FEAT-060** — ritual-check e wiki-guard misurano realtà diverse, e la differenza è invisibile — ritual-check deriva i c · ***Should (P1)***
- 📋 **E10-FEAT-061** — Distribuire il metodo d'audit del codice morto come skill — oggi vive solo come pagina wiki nostra ([[aud · ***Could (P2)***
- 📋 **E10-FEAT-063** — Il perimetro di scan esclude l'installer e i file di radice — sul dogfood source_dirs = ["src", "specs",  · ***Should (P1)***

**E11 · [`multiutente`](../../requirements/multiutente/epic.md)** — 6 aperte

- 📋 **E11-FEAT-M01** — Modello di ownership + modalità mono/team (driver dei default per ogni artefatto) · ***Must***
- 📋 **E11-FEAT-M02** — Collaborazione sul RAG (indice condiviso vs per-utente; store remoto; chi/quando rebuild) · ***Should***
- 📋 **E11-FEAT-M03** — Collaborazione sul Wiki (più curatori; merge della conoscenza; evitare deriva) · ***Should***
- 📋 **E11-FEAT-M04** — Quando/come condividere (cadenze, trigger, automatico vs manuale per indice e wiki) · ***Should***
- 📋 **E11-FEAT-M05** — Segreti & config per-utente (mai versionati, ognuno il proprio ambiente) · ***Must***
- 📋 **E11-FEAT-M06** — Governance leggera (ruoli/responsabilità su wiki e indici) · ***Could***

**E12 · [`usabilita`](../../requirements/usabilita/epic.md)** — 9 aperte

- 📋 **E12-FEAT-003** — Download GloVe con progress/ETA (deterministico, UX-facing) — assorbe l'ergonomia UX-facing da E2/FEAT-01 · ***Should***
- 📋 **E12-FEAT-004** — config-recommender — skill che profila il repo (linguaggi/dimensione/airgapped?/creds cloud?), consiglia  · ***Should***
- 📋 **E12-FEAT-005** — explain / what-is — auto-documentazione dual-audience — skill + comando che rispondono "cos'è / a cosa se · ***Should***
- 📋 **E12-FEAT-006** — tour / onboarding + help CLI più ricco — "cosa può fare Sertor in questo repo?" e un help agent-friendly/ · ***Could***
- 📋 **E12-FEAT-007** — search-diagnose — skill "perché non trova X?": incrocia validate-path + search + osservabilità, interpret · ***Should***
- 📋 **E12-FEAT-008** — search --explain (opzionale) — segnale deterministico per search-diagnose (perché un risultato rankа dove · ***Could***
- 📋 **E12-FEAT-009** — Agente concierge — agente sottile che dispatcha A–D e fa check proattivi; distribuito dual-target · ***Should***
- 📋 **E12-FEAT-011** — Estensione doctor con check-query metadata-filtered (where) — aggiunge a sertor-rag doctor un check-query · ***Should***
- 📋 **E12-FEAT-014** — La prima query RAG di una sessione impiega >2 minuti, e nulla lo dice — misurato sul nodo Acta (corpus 15 · ***Should***

**E13 · [`documentazione-marketing`](../../requirements/documentazione-marketing/epic.md)** — 7 aperte

- 📋 **E13-FEAT-009** — Posizionamento & messaggistica + confronto vs alternative — il «perché Sertor» imperniato sulla fusione c · ***Should***
- 📋 **E13-FEAT-010** — Demo / screencast — mostra il valore (query architetturale → code+doc insieme) in azione · ***Should***
- 📋 **E13-FEAT-011** — Landing / sito pubblico — vetrina del prodotto per il pubblico esterno · ***Could***
- 📋 **E13-FEAT-012** — Blog / contenuti — articoli su valore, casi d'uso, dietro-le-quinte · ***Could***
- 📋 **E13-FEAT-013** — Materiali OSS — README pubblico, CONTRIBUTING, LICENSE (già MIT) e contorno per una repo aperta · ***Could***
- 📋 **E13-FEAT-014** — Guardia DETERMINISTICA contro il drift della documentazione utente — oggi la doc utente (docs/, README.md · ***Should***
- 📋 **E13-FEAT-015** — Un emendamento si referenzia per TITOLO, non per numero — l'annuncio della v0.3.0 diceva ai destinatari « · ***Should (P1)***

**E14 · [`speclift`](../../requirements/speclift/epic.md)** — 3 aperte

- 🔄 **E14-FEAT-002** — Distribuzione via installer — rendere SpecLift/SpecAudit installabili su un ospite esterno che installa S · ***Should***
- 📋 **E14-FEAT-004** — Debrief — consumatore a valle dello stesso primitivo diff→requisito: genera un resoconto/riassunto di ses · ***Could***
- 📋 **E14-FEAT-005** — Guida al test — consumatore a valle: genera indicazioni/casi di test a partire dai requisiti ancorati e d · ***Could***

**E15 · [`fedelta-dogfood`](../../requirements/fedelta-dogfood/epic.md)** — 5 aperte

- 🔄 **E15-FEAT-003** — Artefatti RAG mancanti nel dogfood — portare (o dichiarare assenti con motivo): hook sertor-rag-usage-che · ***Should***
- 📋 **E15-FEAT-004** — Riconciliazione divergenze hand-authored — .mcp.json (dev venv-form vs runtime .sertor/-form), .sertor/.e · ***Should***
- 📋 **E15-FEAT-006** — Template ↔ realtà (staleness inversa) — allineare i template indietro rispetto al dogfood (wiki.config.to · ***Could***
- 📋 **E15-FEAT-011** — Il terzo asse della fedeltà: ciò che facciamo è anche ciò che spediamo? — i due livelli di questa epica ( · ***Should (P1)***
- 📋 **E15-FEAT-014** — Verifica una-tantum: da OGNI versione pubblicata all'ultima — non un gate ricorrente ma una misura, da es · ***Should (P1)***

**E16 · [`evoluzione-modello-wiki`](../../requirements/evoluzione-modello-wiki/epic.md)** — 4 aperte

- 📋 **E16-FEAT-001** — Misurare quanto il core D↔N viene aggirato — dato prima del codice. Costruendo un wiki reale, index.md è  · ***Should (P1)***
- 📋 **E16-FEAT-002** — Backlink deterministici generati dal core — collect.py estrae già i wikilink uscenti per ogni pagina; i b · ***Could (P2)***
- 📋 **E16-FEAT-003** — sertor-wiki-tools plan + coda di riverifica dei «passivi» — scan è a un passo da un update diff-driven: g · ***Could (P2)***
- 📋 **E16-FEAT-004** — Riproducibilità cross-OS verificata + benchmark di scalabilità — «zero-LLM, offline» nell'--help implica  · ***Could (P2)***

---

## 🧭 Nuove funzionalità da discutere (sezione a mano)

> Idee **prima** che diventino feature formali. Stati: 💡 idea · 🗣️ in discussione · 👍 approvata (→ decomporre) · ❌ scartata.
>
> **Quando un'idea è promossa a epica o consegnata, esce da qui:** vive nel backlog dell'epica
> (`requirements/<epica>/epic.md`) + nell'**EXEC** (fonte unica dello stato «consegnato»). Qui restano
> solo le idee **ancora aperte** — non si duplica lo stato delle feature (regola A-12, 2026-07-10).

| Idea | Valore / perché | Note / vincoli | Stato |
|------|-----------------|----------------|-------|
| **Rilevamento attivo dei gap di documentazione** (codice→wiki generativo) | Il residuo *genuino* di FEAT-008: oggi il legame codice↔doc è **passivo** (`get_context`/`related_docs`), manca il **generativo** — il RAG/code-graph che rileva **entità senza pagina wiki** e le **propone** | **Parzialmente consegnata da `distill-audit`** (E10-FEAT-039, v0.1.3). Residuo: gap *dal code-graph* (simboli di codice senza pagina, non solo wiki-interni). Riusa [[code-graph]] + lint C | 🔄 **parziale**; residuo code→wiki |
| **Misurare nella TUI quando si usa il grafo vs il vettoriale/ibrido** | Vedere a runtime **quale metodo di retrieval** serve ogni risposta. Oggi la scheda RAG (E3-FEAT-015) mostra query/verdetto/op-MCP ma **non distingue grafo vs ricerca** | Gli eventi distinti **già esistono** (`hybrid_query`/`retrieve` vs `mcp.<tool>`): serve **aggregarli per metodo**. Il routing vive **nell'agente** (nessun router nel core) → la TUI lo renderebbe **visibile** | 💡 idea (utente, 2026-06-20) |
| **Timeout espliciti su embed/query** (server MCP e adapter) | L'hang della prima query è stato **risolto** (warm-up eager, PR #23); i timeout restano una rifinitura di robustezza | Timeout configurabile in `Settings` + eccezione di dominio | 💡 idea ridimensionata |
| **Connettori per `ingest`** (git/slack/web/…) | `ingest` esiste ma le fonti le porta l'utente; un connettore *ingerisce byte* (lato deterministico), non genera prosa | **Fonte: Nunzio (§7).** **→ mappa su E7** `ingestione-estesa` — cita epica esistente, non voce nuova | 💡 idea esterna → E7 |
| **Segnalare in bacheca le pubblicazioni mai depositate** | Trovate **3 pubblicazioni di altri nodi** (*Acta* ×2, *Studium*, *Nunzio*) affisse ma **mai committate**: invisibili a tutti gli altri. *Affisso* e *depositato* sono due stati che dalla cartella si leggono uguali | Non depositabili da noi (sarebbe scrivere per conto di un altro nodo). Stessa classe di [[guardia-verde-non-e-una-misura]] | 💡 idea (2026-07-30) |

---

## Questioni aperte (tenute così, per ora)

- **Soglie di pertinenza**: non fissate a priori; da misurare su ground-truth reale (DA-003 / DA-1·3).
- **Numerazione**: epica `FEAT-NNN` ≠ `specs/NNN` (vedi sotto) — non riconciliarle a forza, documentare.
- **Server MCP & codice nuovo**: il server **auto-guarisce** da indice/dati *stantii* dopo un re-index
  (ChromaStore auto-refresh + code-graph auto-reload, PR #89/#90 — **nessun riavvio**). Resta necessario
  un **riavvio** del subprocess solo per servire **codice nuovo del server** (`sertor_mcp`).
- **`requirements.md` ↔ `spec.md` si sovrappongono?** *In pratica risolta:* la convenzione consolidata è
  **requirements → specify → clarify → plan → tasks → implement**; l'una o l'altra si salta solo per
  lavori piccoli/meccanici.
- **Il gate pre-merge documentato nel `CLAUDE.md` è incompleto** *(aperto, 2026-07-29)*:
  `testpaths = ["tests"]` fa sì che `uv run pytest -m "not cloud"` raccolga **1372 test su 2504**. Le
  suite `packages/*` vanno lanciate a parte — **sei invocazioni** + `ruff`. Tracciato dentro E15-FEAT-012.

## Visione

Portare capacità **RAG** (ricerca semantica su codice + documentazione) su **qualunque repository**, in
modo riproducibile e production-grade. **Una sola verità interrogabile**: sorgenti (il *come*) e doc/wiki
(il *perché*) coesistono nello stesso corpus; la doc nuova vive **accanto ai sorgenti** via LLM Wiki.
Local-first ↔ cloud per configurazione; riusabile come **libreria**, esposta via **CLI** e **MCP**.

## ⚠️ Due numerazioni (da non confondere)

- **`FEAT-NNN` (epica)** = capacità di prodotto nel backlog (`requirements/<epica>/epic.md`).
- **`specs/NNN`** = ordine **sequenziale** di implementazione. NON coincide con l'epica: `specs/008`
  (meccanica del log) e `specs/009` (decoupling store) sono **lavori abilitanti**, **non** le
  FEAT-008/009 d'epica.

## Come mantenere questa pagina

- Avanzamento feature → aggiorna **solo** il blocco **EXEC** in cima: è la **fonte unica** dello stato
  «consegnato». Gli `epic.md` vi **puntano**, non lo duplicano (regola A-12). È **giudizio del flusso
  principale**, non del `wiki-curator`.
- Capacità consegnata → il suo racconto scende in **[[storico-roadmap]]**; qui resta il rigo di stato.
- Brainstorming → a mano in *Nuove funzionalità da discutere*; l'idea **promossa o consegnata esce di lì**.
- Idea matura → backlog epica + `/requirements` → `/speckit-*`.

## 🔍 Come è stato verificato (2026-07-30)

Non è un rinfresco a memoria — è un censimento contro i sorgenti, ed è ripetibile:

1. **227 righe** di backlog estratte dai 16 `epic.md`, **contate**. La prima passata ne trovava 221: il
   pattern perdeva in silenzio le **6 voci `FEAT-M01..M06`** di E11 (numerazione diversa). *È la ragione
   per cui si conta, invece di fidarsi dell'estrattore.*
2. **L'estrattore stesso era rotto, e in modo che non si vedeva.** Separava le colonne su **ogni** pipe,
   ma in markdown `\|` è un pipe **letterale dentro la cella**: tre righe di E2 lo contengono, le colonne
   slittavano, e come «stato» veniva letta la **coda della frase precedente**. Risultato: 3 feature
   consegnate classificate aperte. Diagnosi per **conteggio celle attese vs reali** → 5 righe anomale,
   0 dopo il fix. *Il rimedio è andato nel parser, non nel contenuto: `\|` era già scritto giusto.*
   Le altre 2 anomalie erano invece contenuto rotto davvero — colonna `Fase` mancante in E13 → riparata.
3. **36 hash di consegna** citati negli stati → verificati **antenati di `master`** con `git merge-base
   --is-ancestor`. Due anomalie, entrambe spiegate e **non drift**: un run-ID di GitHub Actions scambiato
   per hash, e il pin del repo *Sinthari* (esterno).
4. **44 voci ✅ senza riferimento verificabile** → controllate per **esistenza dell'artefatto**. Tutte
   presenti (due «mancanti» erano miei path sbagliati: `services/eval/graph_eval.py` e `indexing.py`).
5. **Voci aperte con menzioni nei commit** → cercati commit di *implementazione*. **Cinque drift trovati
   e corretti**, tutti nella direzione «dichiarata aperta, in realtà consegnata»:
   - **E10-FEAT-029** e **E10-FEAT-030** — «da decomporre» negli `epic.md` pur avendo 2 commit di
     implementazione, e con la costituzione già a v1.6.0 col Principio XIII presente;
   - **E10-FEAT-062** — «su branch, non ancora consegnata» nell'EXEC, mentre è su `master` **e inclusa
     nel tag `v0.4.0`**;
   - **E2-FEAT-012** — vittima del parser (punto 2), in realtà ✅ dal 2026-06-17;
   - **E5-FEAT-012** — «requisiti scritti», ma il **terzo flusso `graph`** di `search_combined` esiste in
     `sertor_mcp/server.py` ed è stato rilasciato in **v0.2.0**. *Sfuggiva perché la facade di libreria
     documenta due flussi: il terzo vive sul vehicle MCP, che è la superficie che l'agente consuma.*
6. **Casi di giudizio, non automatizzabili:** «assorbita da», «soddisfatta in forma composita»,
   «promossa ad altra epica» — un classificatore li legge come aperti o come ritirati, e sbaglia in
   entrambi i versi. Risolti a mano e annotati come override espliciti nello script di censimento.

## Riferimenti

Storico: **[[storico-roadmap]]** · Note utente: [`CHANGELOG.md`](../../CHANGELOG.md) ·
Sintesi per feature: [[hybrid-retrieval]] · [[code-graph]] · [[retrieval-core]] · [[mcp-server]] ·
[[wiki-tools]] · [[architettura-wiki-llm]] · [[constitution]] · [[dogfood-fidelity]] ·
[[guardia-verde-non-e-una-misura]] · [[potere-retrospettivo-di-una-guardia]].
