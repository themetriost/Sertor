# Requisiti — smoke di upgrade: testare la strada che spediamo
<!-- Deriva da: E15-FEAT-012 (epica fedelta-dogfood) -->

## 1. Contesto e problema (perché)

**Testiamo l'installazione. Spediamo aggiornamenti.**

Lo smoke end-to-end esiste, è onesto e gira in CI su quattro matrici
(`tests/integration/test_host_smoke.py`): installa da `git+url@<ref>` — sulle PR, il ref è **il branch
della PR stessa**, quindi verifica il proprio diff — per ogni coppia (assistente, capability), e asserisce
che l'installazione sia verde. Copre un caso reale e lo copre bene: **un ospite nuovo**.

Non esiste **alcun** test che parta dalla **release precedente** e **aggiorni**.

### La misura (2026-07-29)

Contati i riscontri della federazione dal 16/07 al 29/07: **20 riscontri**, di cui ~14 difetti reali (il
resto sono domande, needfinding e risposte).

| Dove sta il difetto | Quanti |
|---|---|
| installer · upgrade · pin · version-check | **7** |
| hook (freschezza, duplicazione) | 3 |
| wiki tooling (scan · gate · lint) | 3 |
| asset distribuiti | 1 |
| **core (retrieval, memoria)** | **1** |

**Un difetto su quattordici nel prodotto; tredici nella superficie di consegna.** E i test stanno
dall'altra parte: **1385** sotto `tests/` (quasi tutti sul core) contro ~600 nei `packages/*/tests`.

### Perché un'installazione da zero non può vederli

Tutti e sette i difetti dell'installer richiedono **un'installazione preesistente e più vecchia**:

| Difetto dal campo | Cosa serve per vederlo |
|---|---|
| il pin `tag = "v0.x"` non si muove (3 nodi indipendenti) | un host che **pinna** a una versione precedente |
| `upgrade` rotto sugli host che pinnano (v0.3.1) | idem — il ramo è **irraggiungibile** su un host ref-less |
| hook **duplicati** al ri-cablaggio (E10-FEAT-032) | un host con l'**hook vecchio** già cablato |
| `--directory` conservato perché «c'era già» | una `.mcp.json` **preesistente** e divergente |
| `PRESENT_DIVERGENT` blocca fix già rilasciati | un file dell'ospite **già presente** |
| falso *behind* del version-check | uno **stamp** scritto da un install precedente |

Un host pulito non ha nulla di preesistente, quindi **non può manifestarne nessuno, per costruzione**.

### E spiega perché li trova sempre qualcun altro

**Nemmeno il dogfood aggiorna.** Il runtime `.sertor/` insegue HEAD con un re-lock (`relock-runtime.ps1`,
eseguito a ogni merge): passa da un commit al successivo, **mai da una versione alla successiva**. È il
terzo limite di [[dogfood-fidelity]] nella sua forma più concreta — il dogfood non è solo *una*
configurazione, è una configurazione che **non esercita il verbo che spediamo**.

L'unico che esegue `sertor upgrade` è **chi riceve il rilascio**. Per questo ogni difetto d'aggiornamento
è arrivato come segnalazione, mai come test rosso.

### La tesi che diventa misura

Questa feature è la **messa in opera** di due pagine già distillate e mai diventate meccanismo:
[[esito-sull-host-vs-forma-dell-asset]] (17/07 — *asserire l'esito su un host che aggiorna, non la forma
dell'asset spedito*) e il terzo limite di [[dogfood-fidelity]] (26/07). Erano **pagine, non gate**; è
esattamente lo schema di E15-FEAT-011 (una pratica che vale per noi e non esiste come vincolo).

## 2. Obiettivi e criteri di successo

**Obiettivo:** prima che un rilascio raggiunga gli ospiti, un host usa-e-getta ha **aggiornato dalla
release precedente a quella corrente**, e gli **esiti** dell'aggiornamento sono stati asseriti.

- **CS-1 (il verbo giusto):** esiste un test che esegue `upgrade` su un host in cui la **release
  precedente è realmente installata** — non simulata, non un fixture scritto a mano.
- **CS-2 (potere retrospettivo):** applicato ai difetti già noti, il meccanismo li **rileva**. Bersaglio:
  ≥ **5 dei 7** difetti installer misurati (pin fermo · upgrade rotto su host pinnato · hook duplicati ·
  entry MCP divergente · falso *behind*).
- **CS-3 (asserisce esiti, non forme):** ogni asserzione riguarda **lo stato dell'host dopo
  l'aggiornamento** (il pin punta alla versione nuova? l'hook è **uno** e aggiornato? la forma
  dell'invocazione MCP è quella corrente? `doctor` è verde?), **mai** il contenuto di un asset nel
  repository sorgente.
- **CS-4 (preserva ciò che è dell'ospite):** l'aggiornamento **non** azzera la configurazione dell'ospite
  (es. il corpus in `.env`) — regressione reale già occorsa in E2-FEAT-022, colta da una prova manuale e
  non dai test.
- **CS-5 (gate di rilascio, non di PR):** il meccanismo è **vincolante prima di un rilascio**; non deve
  appesantire ogni PR (costo: rete + `uvx` + due install completi).
- **CS-6 (parità assistenti):** copre Claude **e** Copilot, come lo smoke d'installazione.
- **CS-7 (fallimento leggibile):** se un'asserzione fallisce, il report dice **quale esito** diverge e
  **su quale host/assistente**, senza richiedere di rieseguire a mano per capire.

## 3. Stakeholder e attori
- **Nodi della federazione** (*Acta*, *Noetix*, *Sinthari*, *Kaelen*, *Studium*, *VM-WorkingFolder*): oggi
  sono **loro** il test d'aggiornamento, involontariamente.
- **Chi rilascia** (flusso principale + utente): deve poter dire «l'aggiornamento funziona» con una prova,
  non con una speranza.
- **CI:** esegue il meccanismo; il costo va speso dove serve.

## 4. Ambito

### In ambito
- Un meccanismo che **installa la release precedente**, **aggiorna** alla corrente e **asserisce gli
  esiti** sull'host risultante.
- La scelta di *quali* esiti asserire, derivata dai difetti realmente occorsi (§1).
- Il punto del ciclo in cui è vincolante (rilascio).
- Copertura per assistente e per capability, coerente con lo smoke esistente.

### Fuori ambito
- **Riprogettare `upgrade`**: qui si *misura*, non si cambia il comportamento.
- I difetti individuali già tracciati (E2-FEAT-023/024, E10-FEAT-043/044): questa feature li avrebbe
  **rilevati**, non li chiude.
- Il **debito del gate documentato** (`testpaths = ["tests"]` → il comando dichiarato «gate vincolante
  pre-merge» nel `CLAUDE.md` copre 1385 test su ~2517, mentre la CI ne esegue sei suite): **correlato ma
  distinto**, vedi §10.
- Il *come* (host usa-e-getta reale vs container, da quale release partire, matrice): **fase di design**.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous):** *The release verification shall exercise the upgrade path from the previously
  released version to the version under release.*
- **REQ-002 (Ubiquitous):** *The previous version shall be really installed on a disposable host before
  the upgrade, and shall not be simulated by hand-written fixtures.*
- **REQ-003 (Ubiquitous):** *The verification shall assert the resulting state of the host after the
  upgrade, not the content of any asset in the source repository.*
- **REQ-004 (Event-driven):** *When the host pins the runtime to an immutable reference, the verification
  shall assert that the pin refers to the version under release after the upgrade.*
- **REQ-005 (Event-driven):** *When a hook is re-wired by the upgrade, the verification shall assert that
  exactly one instance of that hook is wired and that it is the current one.*
- **REQ-006 (Event-driven):** *When host-owned configuration exists before the upgrade, the verification
  shall assert that the upgrade preserved it.*
- **REQ-007 (Ubiquitous):** *The verification shall assert that the health check reports a healthy host
  after the upgrade.*
- **REQ-008 (Unwanted):** *If any asserted outcome diverges, then the verification shall fail and name the
  diverging outcome together with the host and assistant on which it was observed.*
- **REQ-009 (Ubiquitous):** *The verification shall cover every supported assistant.*
- **REQ-010 (Ubiquitous):** *The verification shall be binding before a release is published.*
- **REQ-011 (Optional):** *Where the previous release is not determinable, the verification shall declare
  that condition rather than silently skipping.* — **[DA CHIARIRE: §10]**

## 6. Requisiti non funzionali
- **Costo consapevole:** due installazioni complete + rete (`uvx`) per combinazione. Il perimetro va scelto
  perché il gate resti eseguibile, non perché sia esaustivo.
- **Deterministico nel verdetto:** un fallimento deve essere riproducibile, non un flake di rete; le cause
  ambientali vanno **distinte** da quelle di prodotto (Principio XII: degradare è ammesso, tacere no).
- **Riuso:** lo smoke d'installazione esiste e funziona (script reale + driver `pytest`, invarianti
  anti-drift). Questa feature **estende quella macchina**, non ne costruisce una seconda.
- **Nessun impatto sul prodotto:** `sertor-core` invariato; è verifica.

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo:** richiede rete e `uvx` — come lo smoke esistente, che infatti **si salta** dichiarandolo se
  `uv`/`uvx` non sono nel `PATH`.
- **Assunzione:** «release precedente» è determinabile da un riferimento pubblico stabile (tag / GitHub
  Release). Da confermare in design — è il presupposto di REQ-002.
- **Dipendenza a monte:** la disciplina dei tag di rilascio (già in uso: `v0.3.3` su `d82f127`, verificato
  dereferenziando).
- **Riferimento:** `tests/integration/test_host_smoke.py` + gli script di piattaforma che guida.

## 8. Rischi
- **R-1 — Costo che porta a spegnerlo.** Un gate lento su ogni PR verrebbe aggirato. Mitigato da CS-5
  (gate di **rilascio**) e dal perimetro scelto in design.
- **R-2 — Flake di rete letto come difetto di prodotto** (o viceversa, il caso peggiore): erode la fiducia
  esattamente come la guardia che grida al lupo (v0.3.3). Mitigato dall'NFR di distinzione delle cause.
- **R-3 — Asserzioni troppo deboli.** Un test che verifica solo «l'upgrade è uscito con 0» ripeterebbe il
  difetto che vuole chiudere: `upgrade` **usciva verde** mentre non muoveva il pin. CS-3 è il presidio.
- **R-4 — Falsa sicurezza sul residuo.** Ne intercetterebbe 5 su 7: i due restanti (e i difetti dei nodi
  con configurazioni che non abbiamo) **restano scoperti**. Va detto, non implicito.
- **R-5 — Deriva dell'asserzione.** Gli esiti da asserire crescono coi difetti trovati; senza un posto
  dichiarato dove aggiungerli, la lista invecchia ([[riassunto-invecchia-senza-riconciliatore]]).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003, REQ-008, REQ-010 (il cuore: verbo giusto · host reale · esiti ·
  fallimento leggibile · vincolante al rilascio).
- **Should:** REQ-004, REQ-005, REQ-006, REQ-007 (le quattro asserzioni derivate dai difetti reali),
  REQ-009 (parità assistenti).
- **Could:** REQ-011.
- **Won't (qui):** riprogettare `upgrade`; chiudere i difetti individuali già tracciati.

## 10. Domande aperte (da sciogliere in `clarify`)
- **DA-1 — Da quale versione si parte?** L'**ultima release** (caso reale più frequente) oppure **più
  salti** (un ospite può aggiornare da due versioni indietro — *Acta* l'ha fatto: 0.3.0 → 0.3.3 in un
  passo, ed è **esattamente** la condizione in cui è emerso il difetto del pin). Il secondo copre di più e
  costa di più.
- **DA-2 — Quanto perimetro.** Tutte le combinazioni (assistente × capability) o un sottoinsieme scelto?
  Lo smoke d'installazione ne ha quattro; l'upgrade le raddoppierebbe come tempo.
- **DA-3 — Dove vive la lista degli esiti asseriti**, così che aggiungerne uno dopo un nuovo difetto dal
  campo sia un gesto ovvio e non un refactor (R-5).
- **DA-4 — Rapporto col debito del gate documentato** (`testpaths` → 1385 su ~2517): si corregge qui,
  dichiarando nel `CLAUDE.md` il comando reale, o è una riga di backlog a parte? *Raccomandazione:
  correggere la documentazione **subito e a parte**, perché è un errore di un documento sempre attivo — e
  tenere questa feature sul suo obiettivo.*
- **DA-5 — Comportamento quando la release precedente non è determinabile** (REQ-011): dichiarare e
  passare, o fallire?

## 11. Fuori ambito promossi
- **Debito del gate documentato** (§4, DA-4): se non si chiude qui, va una riga di backlog **prima** che
  questa feature entri in `plan` — è la stessa classe di difetto che questa feature presidia (un artefatto
  dichiara una copertura che non ha).

---

## Commit proposto
`docs(requirements): E15-FEAT-012 — smoke di upgrade, testare la strada che spediamo (EARS)`
