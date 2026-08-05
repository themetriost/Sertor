# Epica — Separazione dell'ecosistema in nodi installabili

> **Origine:** il piano di migrazione `specs/127-separazione-quattro-prodotti/migration-plan.md`
> (2026-07-31), con l'**inventario file-per-file** in `file-inventory.md`. Ogni numero citato qui è
> **misurato sul repo**, non stimato.
>
> **Perché questa epica esiste:** fino al 2026-08-05 il lavoro più grosso in corso viveva **solo**
> dentro `specs/127-*` e nel blocco EXEC della roadmap, senza corrispondere ad alcuna `FEAT` di alcuna
> epica. È esattamente ciò che la regola sugli *Out of Scope* vieta — un lavoro reale che vive solo
> dentro `specs/`, quindi invisibile a chiunque legga il backlog per sapere «cosa manca».
> *Verificato prima di crearla:* nessuna delle 16 epiche preesistenti copre la separazione;
> **E15 `fedelta-dogfood`** è la più vicina ma il suo *Fuori ambito* **esclude esplicitamente**
> «riscrivere gli installer», che è precisamente il cuore di FEAT-002/004.

## 1. Visione e problema (perché)

Sertor è cresciuto contenendo **quattro prodotti distinti** che condividono un repo per ragioni
storiche, non di design: il **RAG** (retrieval, code-graph, memoria, osservabilità, MCP), il
**sistema-wiki** (nucleo deterministico + layer agentico + rituale + gate), il **metodo**
(governance/SDLC, SpecKit, costituzione) e il **prototipo** congelato.

La convivenza ha un costo che ora è misurato, non percepito:

- **Il debito si attribuisce per collocazione, non per contenuto.** **43 delle 67 voci** di E10
  `debito-tecnico` nominano il wiki: un prodotto porta il debito di un altro, e nessuna metrica lo
  dice.
- **La conoscenza si duplica in modo invisibile.** «Dove va una skill per Claude vs Copilot» è scritta
  **due volte** — Rust in Kaelen, Python nel kit d'installazione — in **due repo e due linguaggi**,
  quindi fuori dalla portata di qualunque guardia che conosca un solo repo. Non è un difetto trovato:
  è un difetto **non trovabile** con gli strumenti attuali.
- **Chi vuole solo il wiki deve prendersi il RAG**, e viceversa: l'unità di distribuzione non
  corrisponde all'unità di valore.

La visione: **ogni prodotto è un nodo autonomo**, rilasciabile e installabile su un ospite terzo,
host-agnostico su **Claude e Copilot CLI**, esattamente come Sertor oggi — con il proprio installer,
i propri asset in forma nativa per entrambi gli assistenti, le proprie guardie di parità, il proprio
ciclo di rilascio e il proprio gate d'aggiornamento. **Nessun nodo può essere «quello che si installa
a mano».**

E un **quinto attore**, emerso sciogliendo le decisioni e non previsto dalla prima stesura: **Kaelen**
diventa il **motore d'installazione dell'ecosistema** e il proprietario dello **schema del manifest di
nodo**. I nodi smettono di implementare l'installazione: la **dichiarano**.

| Nodo | Cosa è | Stato |
|---|---|---|
| **Sertor** | Il RAG | esistente — si alleggerisce |
| **Thesmion** | Il sistema-wiki | folder vuoto, non ancora un repo git |
| **Sulcimen** | Il metodo (governance/SDLC) | folder vuoto, non ancora un repo git |
| **ProtoSertor** | Il prototipo congelato | ✅ **nato** (2026-07-31) — nodo non gestito da noi |
| **Kaelen** | Il motore + lo schema del manifest | esistente (spike Rust, 16.628 righe) |

> **SpecLift/SpecAudit non entrano in nessuno dei quattro** (decisione D3): appartengono a
> **Sinthari**, che si dichiarerà nodo e li distribuirà. Smettiamo di vendorarli.

## 2. Ambito

### In ambito

- **Nascita dei nodi** Thesmion e Sulcimen come repo autonomi, **con la storia git preservata**
  (`git filter-repo`, mai copia piatta).
- **Il motore d'installazione unico** in Kaelen, e la trasformazione dei **piani-in-codice** in **dati
  dichiarativi** letti da uno schema versionato.
- **L'estinzione della duplicazione cross-repo/cross-linguaggio** sui path d'assistente.
- **La ripartizione tracciata** di `requirements/`, `specs/` e `wiki/` fra i nodi, con verdetto scritto
  per ogni riga e conteggio che torna.
- **Sertor ripulito**, che riceve wiki e metodo **come un ospite qualsiasi**.
- **La verifica su host pulito** che i tre nodi convivono senza pestarsi.
- **La continuità per gli ospiti esterni** già installati (Acta, Kaelen, Noetix, Sinthari, …).

### Fuori ambito

- **Il repo di ProtoSertor.** È nato ed è un nodo come gli altri: *le sue questioni le risolve lui*
  (decisione utente, 2026-07-31). Qui resta solo ciò che compete a Sertor.
- **La distribuzione di SpecLift/SpecAudit** — è di Sinthari (D3). Qui si registra solo la
  **rimozione del vendoring**, che chiude E14-FEAT-002.
- **Cambi funzionali ai prodotti.** La separazione **non è l'occasione** per aggiungere capacità: un
  nodo che nasce deve fare *esattamente* ciò che faceva la sua fetta prima del taglio.
- **Il nome pubblico del kit**, **la sorte di E11 `multiutente`**, **se le pagine-lezione meritino un
  quinto nodo** (E9 `second-brain`) e **se ProtoSertor debba restare privato** — quattro decisioni che
  il piano dichiara esplicitamente di **non** prendere.
- **Unificare le pagine-lezione** in un nodo proprio: il piano le **copia** in ciascun nodo, che è la
  scelta reversibile.

## 3. Criteri di successo (misurabili, tech-agnostici)

| # | Criterio | Come si falsifica |
|---|---|---|
| **SC-1** | Ogni nodo supera **tutti e 12** i requisiti di rilascio host-agnostico (§7) | una casella non verificata = nodo non «fatto» |
| **SC-2** | Installare un nodo **da manifest** lascia l'host nello **stesso stato** che installarlo da codice | confronto dell'esito su host usa-e-getta, prima e dopo — non «il motore funziona» |
| **SC-3** | Su un host pulito, **3 nodi × 2 assistenti = 6 installazioni** riescono, e i tre installer **non si sovrascrivono** su `settings.json`/`.mcp.json`/`CLAUDE.md`/`.gitignore` | ogni blocco è posseduto dal suo marker; `uninstall` di un nodo non rompe gli altri due |
| **SC-4** | La duplicazione «dove va una skill» **non può più esistere**: Rust e Python **derivano** i path dallo stesso schema | guardia: zero path d'assistente hardcoded nei due linguaggi |
| **SC-5** | **Zero righe orfane** nella ripartizione di `requirements`/`specs`/`wiki` | conteggio prima/dopo che torna, con verdetto scritto per ogni riga |
| **SC-6** | La **storia git** sopravvive in ogni nodo | `git log` non vuoto su file campione; per ProtoSertor: **35 commit dal 2026-05-28** ✅ |
| **SC-7** | Un ospite esterno che aggiorna **non si rompe**, e l'avviso **nomina il sostituto** | alias deprecati esercitati da un test; upgrade che dice *cosa è diventato cosa* |
| **SC-8** | Sertor, a fine corsa, riceve wiki e metodo **dall'esterno** e il rituale continua a funzionare | il gate `wiki-guard` gira su Sertor **essendo installato da Thesmion**, non essendone parte |

## 4. Stakeholder e attori

- **L'utente/proprietario dell'ecosistema** — decide i confini e l'ordine; ha sciolto le 7 decisioni.
- **Gli ospiti esterni già installati** (Acta, Kaelen, Noetix, Sinthari, VM-WorkingFolder, …) — hanno
  **cablato** `sertor install wiki` e `sertor-wiki-tools` in hook e istruzioni, non solo in doc: sono
  la ragione per cui la continuità è un criterio e non una cortesia.
- **Un ospite terzo futuro** — deve poter installare un nodo qualsiasi senza sapere nulla degli altri.
- **Un nodo di terzi** — deve potersi dichiarare con un proprio manifest **senza toccare Kaelen**.
- **Gli agenti** (Claude, Copilot CLI) — consumano gli asset; la parità fra i due è un vincolo, non un
  obiettivo secondario.

## 5. Vincoli, assunzioni e dipendenze

**Vincoli**

- **Ogni nodo host-agnostico su entrambi gli assistenti**, in forma **nativa** — mai hack di compat.
- **`master` sempre verde**: l'ordine delle fasi è scelto per rischio crescente, e ogni fase ha un
  criterio d'uscita falsificabile.
- **Storia git preservata** (`git filter-repo`) — 601 spec e 205 pagine la cui giustificazione **è** la
  storia.
- **Perimetro congelato**: nessuna feature nuova sui sottoalberi in migrazione finché la separazione
  non chiude.
- **Nessun cambio funzionale** durante il taglio (vedi *Fuori ambito*).

**Assunzioni (misurate, non supposte)**

- I tre nodi non-RAG sono **già quasi separati**: `sertor-flow` e `prototype/` hanno **zero**
  accoppiamento col core; `install-kit` **zero**. `wiki_tools` ne ha **quattro**, di cui due lazy.
- Il taglio più costoso è il **logging** (11 import), **non** l'architettura.
- Il rag-sync (`indexing.py`) è **già progettato per il taglio**: import lazy, `indexer_factory`
  iniettabile, no-op dichiarato se disabilitato → Thesmion può dipendere da Sertor come **extra
  opzionale**.

**Dipendenze**

- **Kaelen** deve accettare il ruolo di motore (D1) — è esistente ma è uno **spike**, non ancora un
  prodotto.
- **Sinthari** deve dichiararsi nodo per assorbire SpecLift/SpecAudit (D3).
- Le sette trappole di [[cosa-non-viaggia-in-una-migrazione]] vanno **rilette prima** di ogni fase di
  estrazione: F1 le ha pagate sul caso più semplice.

## 6. Rischi

| # | Rischio | Perché è concreto | Mitigazione |
|---|---|---|---|
| **R1** | **Le righe di E10/E15 si perdono** nella ripartizione | 28 voci aperte, trasversali per costruzione; un classificatore lessicale sbaglia in **entrambi** i versi — già misurato il 30/07 | verdetto **scritto** per ogni riga; conteggio prima/dopo che deve tornare (FEAT-011) |
| **R2** | **Il rituale si spezza** durante la nascita di Thesmion | il gate `wiki-guard` blocca lo Stop: se Thesmion non è ancora installabile, Sertor resta senza rituale | si rimuove da Sertor **solo dopo** che l'installazione dall'esterno è verificata |
| **R3** | **Tre installer si pestano** sugli stessi file dell'ospite | `settings.json`, `CLAUDE.md`, `.mcp.json` scritti da tre sorgenti | è un **criterio d'uscita** (SC-3), non un controllo finale |
| **R4** | **La storia git si perde** | è la giustificazione di 806 artefatti | `filter-repo`, mai copia piatta; verifica su file campione |
| **R5** | **Il motore diverge** in più copie | è **già successo** con le pratiche standing non distribuite | un solo motore (D1); se mai due, guardia di parità byte obbligatoria |
| **R6** | **Gli ospiti esterni si rompono** | hanno cablato i comandi in **hook e istruzioni**, non solo in doc | alias deprecati per una release, con avviso che **nomina** il sostituto (FEAT-014) |
| **R7** | **Il dogfood perde fedeltà** durante la transizione | per un periodo Sertor avrebbe il wiki «a metà» | atomicità per fase: o il wiki è dentro, o è installato — **mai in mezzo** |
| **R8** | **Il CHANGELOG/EXEC di ogni nodo nasce vuoto** e la storia sembra inesistente | è la malattia di [[riassunto-invecchia-senza-riconciliatore]] | ogni nodo nasce con una voce di log «nascita del nodo» che **punta** all'archivio in Sertor |
| **R9** | **La classificazione di proprietà degli artefatti passa nello schema com'è** | il modello è **binario** (`owned`/`shared`) e non ha casella per i **punti di estensione** — vedi [[punti-di-estensione-condivisi]] e E10-FEAT-068 | lo schema del manifest (FEAT-003) deve prevedere il terzo caso: *la correttezza va nello schema, non nella riga* |

## 7. Requisiti trasversali (EARS)

Valgono per **ogni** nodo dell'ecosistema, e sono la forma verificabile della checklist dei 12
requisiti di rilascio.

- **REQ-001** — The node shall provide its own installer exposing `install`, `upgrade` and `uninstall`.
- **REQ-002** — The node shall support `--assistant claude`, `--assistant copilot-cli` and `all`.
- **REQ-003** — The node shall ship its assets in each assistant's **native** form, with no
  compatibility shim.
- **REQ-004** — The node shall ship hooks that run without PowerShell, on Windows, macOS and Linux.
- **REQ-005** — The node shall own its instruction block through markers, and regenerate it in place
  on re-install.
- **REQ-006** — When writing a host file that a third party may also write, the node shall **merge**,
  never overwrite.
- **REQ-007** — If a host file to be written contains declarations the node does not own, then the
  node shall leave it untouched and **report** what it skipped and why.
- **REQ-008** — The node shall carry `VERSION`, `CHANGELOG`, a git tag and a published Release.
- **REQ-009** — Where an auto-updater is installed, the node shall notify of a newer version and shall
  **not** update by itself.
- **REQ-010** — The node shall pass an installation smoke on 2 operating systems × 2 assistants.
- **REQ-011** — The node shall pass an **upgrade gate** on the jump its hosts will actually make, with
  every outcome **named** and zero `n/a`, read from the logs and not deduced from the exit code.
- **REQ-012** — The node shall ship user documentation (`install.md` + a per-assistant quick-start).
- **REQ-013** — The node shall install itself from its own installer, and its `doctor` shall be green.
- **REQ-014** — When a command or asset is renamed, the node shall keep a deprecated alias for one
  release and shall emit a warning that **names the replacement**.

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **ProtoSertor è un nodo autonomo** — il prototipo esce da Sertor con la storia dalla nascita del progetto, corpus incluso | Rompe il ghiaccio sulla procedura `filter-repo` sul caso a rischio zero (zero import), pagando le trappole prima di applicarla dove girano i gate | **Must** | ✅ **CONSEGNATA** (2026-07-31) — vedi EXEC. 35 commit dal 2026-05-28, zero contaminazione verificata, 81 file e 1,4 GB fuori da Sertor. Le sette trappole → [[cosa-non-viaggia-in-una-migrazione]] |
| FEAT-002 | **Il motore d'installazione unico, casa Kaelen** — il kit (2.552 righe) + i suoi 24 test + le 37 guardie di meccanismo si trasferiscono in Kaelen | Una sola implementazione dell'installazione per tutto l'ecosistema, invece di una per nodo | **Must** | 📋 da decomporre |
| FEAT-003 | **Schema `node.manifest.v1.json`: un nodo si dichiara** — cos'è un nodo (identità, artefatti, surface per agente, hook, blocchi a marker, merge, lifecycle, template `.env`) | Un nodo di terzi si dichiara **senza toccare Kaelen**; è la condizione perché l'ecosistema sia aperto e non un club | **Must** | 📋 da decomporre — ⚠️ deve prevedere il **terzo caso di proprietà** (R9) |
| FEAT-004 | **I piani-in-codice diventano dati** — 2.627 righe (`install_rag` 1.324 · `install_wiki` 713 · `install_governance` 590) convertite in manifest, una alla volta | È la fase che domina lo sforzo (**8×**). Criterio: l'installazione da manifest lascia l'host nello **stesso stato** di quella da codice (SC-2) | **Must** | 📋 da decomporre |
| FEAT-005 | **La duplicazione cross-linguaggio si estingue** — Rust e Python leggono lo **stesso** schema; `Agent::install_subpath` smette di codificare i path e li deriva | Chiude un duplicato **invisibile per costruzione**: vive in due repo e due linguaggi, quindi nessuna guardia di un singolo repo può vederlo | **Must** | 📋 da decomporre |
| FEAT-006 | **I gusci dei nodi delegano al motore** — `sertor install …` resta il comando che l'ospite vede, ma esegue il motore unico | L'ospite non paga la riorganizzazione interna: stesso comando, stesso esito | **Should** | 📋 da decomporre — include la scelta se Kaelen sia dipendenza pinnata o risolta a runtime |
| FEAT-007 | **Kernel condiviso e schema evento versionato** — Thesmion reimplementa `log_event` + 2 errori (~200 righe); lo schema dell'evento d'osservabilità è condiviso e versionato | Recide la sutura più costosa (11 import) senza creare una dipendenza inversa fra nodi | **Should** | 📋 da decomporre |
| FEAT-008 | **Sulcimen — il nodo del metodo** — governance/SDLC, SpecKit, costituzione; installer, asset per due assistenti, CI, smoke, gate d'aggiornamento, doc | Il metodo diventa installabile su qualunque progetto, indipendentemente dal RAG | **Must** | 📋 da decomporre — include la **rimozione del vendoring** di SpecLift/SpecAudit, che chiude **E14-FEAT-002** |
| FEAT-009 | **Thesmion — il nodo del sistema-wiki** — nucleo deterministico, layer agentico, rituale, gate; `thesmion[rag]` come extra opzionale | Il sistema-wiki diventa installabile senza portarsi il RAG, e il RAG diventa opzionale per chi vuole solo la memoria scritta | **Must** | 📋 da decomporre — **la più intrecciata: 4 suture** |
| FEAT-010 | **Sertor ripulito riceve wiki e metodo come un ospite** — perde il verbo `wiki`, la prosa dogfood si riduce al RAG, i blocchi arrivano **installati** | È la prova che la separazione è reale e non nominale: il rituale funziona su Sertor **essendo installato da Thesmion** (SC-8) | **Must** | 📋 da decomporre |
| FEAT-011 | **Ripartizione tracciata di requirements/specs/wiki** — verdetto **scritto** per ogni riga, conteggio prima/dopo che torna | Mitiga R1, il rischio più concreto: 28 voci aperte trasversali, dove un classificatore lessicale sbaglia in entrambi i versi | **Must** | 📋 da decomporre — **43 delle 67 voci di E10 nominano il wiki** |
| FEAT-012 | **La checklist dei 12 requisiti di rilascio, per ogni nodo** — resa eseguibile invece che promessa | Un nodo non è «fatto» finché non le supera tutte e dodici; è la forma verificabile di REQ-001..014 | **Must** | 📋 da decomporre |
| FEAT-013 | **Verifica su host pulito: 3 nodi × 2 assistenti** — installazione, upgrade, conflitti sui file condivisi, `uninstall` che non rompe gli altri | *«La verifica che vale più di tutte»*: il criterio del goal dimostrato, non affermato (SC-3) | **Must** | 📋 da decomporre |
| FEAT-014 | **Continuità per gli ospiti esterni** — alias deprecati per una release, con avviso che **nomina** il sostituto; l'`upgrade` dice *cosa è diventato cosa* | Gli ospiti hanno cablato i comandi in **hook e istruzioni**: senza questo, la separazione li rompe in silenzio (R6) | **Should** | 📋 da decomporre |
| FEAT-015 | **Federazione e rilascio coordinato** — annuncio dei nodi nuovi in bacheca, aggiornamento dei nodi esterni, rilascio coordinato, rimozione degli alias **una release dopo** | Chiude il ciclo: i nodi esistono per gli altri solo quando sono annunciati e installabili | **Should** | 📋 da decomporre |
| FEAT-016 | **Estrazione delle tracce per-nodo dai log** — i log restano invariati (sono storia); estrarne la traccia di ciascun nodo è un di più | Ogni nodo nasce con una storia leggibile invece che con un CHANGELOG vuoto (R8) | **Could** | 📋 da decomporre |

> **Come leggere lo stato:** l'**EXEC** di `wiki/syntheses/roadmap.md` resta la **fonte unica** dello
> stato «consegnato» (regola A-12). Le righe qui **puntano** all'EXEC, non ne duplicano merge/PR/date.

## 9. Domande aperte

1. **[DA CHIARIRE: il nome pubblico del kit/motore]** — `agentkit-install`, `install-kit`, altro. È un
   nome pubblico, quindi una scelta a senso unico una volta annunciato.
2. **[DA CHIARIRE: Kaelen dipendenza pinnata o risolta a runtime?]** — incide su cosa succede a un
   ospite quando il motore avanza e il nodo no. *(Generata dalle decisioni, §3.0.1 del piano.)*
3. **[DA CHIARIRE: le pagine-lezione meritano un quinto nodo?]** — il piano le **copia** in ciascun
   nodo (scelta reversibile); unificarle è una decisione successiva che non blocca nulla. Interseca
   E9 `second-brain`.
4. **[DA CHIARIRE: la sorte di E11 `multiutente`]** — 6 voci, 0 consegnate, e riguarda **tutti e tre**
   i nodi: non è chiaro chi la eredita.
5. **[DA CHIARIRE: ProtoSertor resta privato mentre gli altri sono pubblici?]**
6. **[DA CHIARIRE: quando SpecLift/SpecAudit entrano in un nodo dedicato?]** — D3 è dichiarata
   **provvisoria**: Sinthari li distribuisce *per ora*.

## 10. Riferimenti

- **Piano di dettaglio:** [`specs/127-separazione-quattro-prodotti/migration-plan.md`](../../specs/127-separazione-quattro-prodotti/migration-plan.md)
  — 8 fasi con criteri d'uscita falsificabili, 7 decisioni sciolte, matrice artefatto→destinazione,
  vista per nodo.
- **Inventario file-per-file:** [`file-inventory.md`](../../specs/127-separazione-quattro-prodotti/file-inventory.md).
- **Metodo di misurazione dei confini:** [[confine-di-prodotto-misurato]].
- **Le trappole di un'estrazione:** [[cosa-non-viaggia-in-una-migrazione]] — da rileggere **prima** di
  ogni fase.
