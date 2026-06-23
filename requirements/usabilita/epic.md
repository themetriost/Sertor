# Epica — Usabilità (esperienza di setup, configurazione e uso)

> Livello: **epica (E12)**. Non aggiunge un nuovo motore di retrieval: rende **usabile** ciò che già
> esiste. Costruisce uno **strato di esperienza** — skill agentiche + un agente *concierge* + poche
> primitive deterministiche mancanti + documentazione *self-describing* dual-audience — sopra i
> vehicle (CLI/MCP) di Sertor. Si decompone in `requirements/usabilita/<feature>/requirements.md` (EARS).
>
> **Gate missione & Costituzione (Principio X — host-agnosticità).** L'usabilità è *periferica* al
> differenziatore (qualità del retrieval reso all'agente), ma **serve l'adozione e la portabilità**:
> *un agente che sa installare, configurare e diagnosticare Sertor da solo su un ospite qualunque È
> host-agnosticità reale*. Vincolo non negoziabile (**Principio D↔N**): l'intelligenza vive nelle
> **skill/agenti dell'ospite** sopra i vehicle; **il core non chiama mai un LLM**.

## 1. Visione e problema (perché)

L'esperienza di **setup, configurazione e uso** di Sertor oggi **non è adeguata**. Il problema non è
l'assenza di funzioni — è che l'attrito è **reale ma sparso**: i singoli errori spesso si
auto-spiegano (`GloveUnavailableError` nomina le due vie d'uscita; `ConfigError` nomina la chiave
mancante), ma **manca un flusso unificato che li prevenga o li spieghi prima** che l'utente ci sbatta.

Attriti concreti rilevati (ricognizione del codice):

- **Setup:** `uvx … sertor install rag` → riempire `.sertor/.env` **a mano** → `sertor-rag index .`.
  Il download GloVe (~822 MB) non ha progress/ETA; `pip` non risolve il workspace `uv` (serve `uvx`);
  la cache `uvx` resta stale senza `--refresh`; il layout `.sertor/` è opaco.
- **Configurazione:** il wizard `sertor configure` esiste (catena flag→env→prompt, CI-safe), ma i knob
  sono molti, **backend≠store** confonde, e **non esiste un "ha funzionato?" deterministico**: il probe
  `--check` è *deferred* perché manca un `sertor-rag check`/doctor.
- **Uso/diagnosi:** quando "il RAG non trova", gli strumenti ci sono (`eval validate-path`,
  `eval run --json`, `observe`, `low_confidence`) ma sono **da esperto e scollegati** — nessun "perché
  non ha trovato X? → ecco la causa e il fix".
- **Comprensione:** non c'è un modo **inline e consultabile** per chiedere "cos'è questo? a cosa serve?
  cosa devo aspettarmi? come si usa?" — né per l'agente né per un umano che non conosce gli internals.

La **visione**: portare l'esperienza da "funziona se sai cosa fare" a "ti guida, ti verifica e ti
spiega". Lo strumento è l'**agente frontier dell'ospite** che usa i vehicle deterministici di Sertor
(come già fanno `wiki-author`/`eval-suite-author`), affiancato dalle **poche primitive deterministiche
mancanti** senza cui l'agente resterebbe cieco (su tutte un `sertor-rag doctor`).

> Il *come* (stack, struttura del codice, schema dei comandi) è materia della **fase di design** a
> valle. Qui solo *cosa* e *perché*.

## 2. Ambito

Questa epica è **owner del layer di esperienza utente**: possiede l'**esperienza** e **assorbe gli
item UX-facing** disseminati in altre epiche, mentre i **meccanismi** sottostanti **restano nelle
epiche d'origine come dipendenze** (nessuna duplicazione — solo cross-reference).

### In ambito
- **Verifica e salute (deterministica):** un comando `sertor-rag doctor` che risponde "ha funzionato?"
  (env completo? provider raggiungibile? indice presente/fresco? MCP vivo?).
- **Guida agentica al setup:** skill + ramo dell'agente *concierge* che conduce install → configure →
  verify conversando, scegliendo il provider dal contesto e riempiendo `.env` via `configure --set`.
- **Configurazione guidata:** skill che profila il progetto e **consiglia** provider/backend/engine,
  spiegando `backend≠store`, e applica via il wizard esistente.
- **Diagnosi d'uso:** skill che risponde "perché non trova X?" incrociando i segnali già esistenti e
  proponendo il fix azionabile.
- **Scoperta & auto-documentazione *dual-audience*:** un modo **inline e consultabile** (agente + umano
  non-interno) per "cos'è / a cosa serve / cosa aspettarsi / come si usa", + un tour delle capacità +
  un help CLI più ricco.
- **Orchestrazione:** un **agente *concierge*** sottile che dispatcha le skill sopra e fa check
  proattivi, distribuito dual-target (Claude/Copilot) col pattern d'installazione esistente.
- **Poche primitive deterministiche UX-facing** assorbite da altre epiche (vedi mapping sotto): progress
  del download, hint `--refresh`, messaggi di primo-uso.

### Mapping di confine (item assorbiti vs meccanismi che restano)
- **da E2 `sertor-cli`:** il probe `--check` (FEAT-003 US5, *deferred*) → si concretizza qui come
  **`sertor-rag doctor`**; l'ergonomia **UX-facing** (progress GloVe, hint `--refresh`, messaggi
  primo-uso) → qui. *Restano in E2:* packaging, lifecycle (install/upgrade/uninstall), `install-kit`.
- **da E3 `osservabilità`:** la **diagnosi user-facing** ("spiega perché non trova / risultati deboli")
  → qui. *Resta in E3:* lo store eventi, l'aggregazione e il motore TUI (usati come dipendenza).
- **da E10 `debito-tecnico`:** la **freschezza user-facing** ("indice stantio → fai X", reconnect MCP)
  → qui come skill. *Resta in E10/`sertor-core`:* l'enforcement deterministico via hook (FEAT-011) e il
  refresh incrementale (meccanismi).

### Fuori ambito
- **Il core che chiama un LLM** (Principio D↔N): ogni intelligenza sta nelle skill/agente dell'ospite.
- **I meccanismi sottostanti:** observability store/TUI (E3), refresh incrementale + hook freschezza
  (`sertor-core`/E10), packaging/lifecycle/install-kit (E2) — questa epica li **consuma**, non li
  reimplementa.
- **Web GUI / dashboard nel browser** (eventuale, è dell'epica osservabilità).
- **Nuovi motori o tecniche di retrieval** (epica `retrieval-qualita`).

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (dal nulla a verificato):** un utente nuovo arriva da repo non configurato a **RAG funzionante
  e verificato** (un `doctor` "tutto verde") seguendo la guida agentica, **senza** leggere gli internals.
- **CS-2 (verifica deterministica):** `sertor-rag doctor` riporta con precisione lo stato di env /
  provider / indice (presenza+freschezza) / MCP, con esito azionabile (cosa manca e come rimediare).
- **CS-3 (diagnosi azionabile):** una domanda "perché non trova X?" produce, via skill, una **causa
  probabile + un fix concreto** (es. re-index, provider, soglia, indice stantio) ancorato ai segnali
  reali, non una risposta generica.
- **CS-4 (auto-documentazione dual-audience):** "cos'è / a cosa serve / come si usa X" riceve una
  risposta **sia per l'agente sia per un umano non-interno**, da una reference che **viaggia con
  l'install** (non richiede l'accesso al repo di Sertor).
- **CS-5 (host-agnostico & installabile):** tutti gli asset di usabilità (skill, agente, comando, hook)
  sono **host-agnostici** e installabili su **Claude e Copilot** via `sertor install`, con guardia di
  parità (come per gli asset esistenti).
- **CS-6 (additività & D↔N):** a leve spente il comportamento è identico a oggi; nessun percorso del
  **core** invoca un LLM (verificabile).
- **CS-7 (no duplicazione):** ogni item "owner" di questa epica ha un **cross-ref** nell'epica d'origine;
  i meccanismi non sono ricopiati.

## 4. Stakeholder e attori
- **Utente nuovo / chi installa su un ospite:** vuole arrivare a "funziona" senza conoscere gli internals.
- **Owner/maintainer (tu):** vuole meno attrito ricorrente (setup di nuovi ospiti, diagnosi rapida).
- **Agente frontier dell'ospite (Claude/Copilot):** è **l'esecutore** delle skill di guida/diagnosi e il
  primo consumatore dell'auto-documentazione.
- **Umano non-tecnico / stakeholder:** legge l'auto-documentazione dual-audience ("cosa aspettarsi").
- **I vehicle deterministici (CLI/MCP):** sorgente dei segnali che le skill orchestrano (devono
  esporne abbastanza — da qui le primitive nuove).

## 5. Vincoli, assunzioni e dipendenze
- **D↔N (non negoziabile):** il core non chiama LLM; le feature agentiche sono skill/agenti dell'ospite
  che usano i vehicle. Le primitive nuove (es. `doctor`) sono **deterministiche** e testabili offline.
- **Riuso del pattern di distribuzione:** skill/agenti/hook viaggiano via `sertor install` con render
  **dual-target** da fonte unica (Claude `.claude/skills` ↔ Copilot `.github/skills`) e guardia di
  parità — già collaudato (`wiki-author`, `eval-suite-author`, `eval-feedback`).
- **Dipendenze inter-epica (consumo, non reimplementazione):**
  - **E2 `sertor-cli`:** wizard `configure` e `validate_backend` (fonte unica dei campi richiesti),
    installer/lifecycle. `doctor` concretizza il `--check` deferred.
  - **E3 `osservabilità`:** store eventi / report / segnali (`low_confidence`, freschezza) che la
    diagnosi user-facing interpreta.
  - **`sertor-core`/E10:** refresh incrementale (freschezza dell'indice) e l'eventuale hook
    d'enforcement (FEAT-011) come complemento deterministico.
- **Local-first & host-agnostico:** la guida e la diagnosi funzionano su qualunque ospite; ciò che varia
  sta in config/asset, non in assunzioni hardcoded (Principio X).
- **Calibra al valore:** molte voci sono skill leggere (istruzioni) — non sovra-spec-are; le primitive
  deterministiche (`doctor`, progress, help) seguono il flusso SpecKit quando lo meritano.
- **Assunzione:** l'agente frontier è disponibile sull'ospite (è il presupposto del modello agentico di
  Sertor); dove non lo è, restano i vehicle deterministici e l'auto-documentazione umana.

## 6. Rischi
- **R-1 — Sovrapposizione con E2/E3/E10:** "owner del layer UX" rischia di duplicare scope. Mitigazione:
  mapping di confine esplicito (§2) + cross-ref obbligatori + meccanismi non ricopiati (CS-7).
- **R-2 — Skill cieche senza segnali:** un agente diagnostica male se i vehicle non espongono lo stato.
  Mitigazione: le primitive deterministiche (su tutte `doctor`) sono **prerequisito** delle skill.
- **R-3 — Scope creep verso "UX generica":** rischio di costruire wizard/onboarding fini a sé stessi.
  Mitigazione: ancoraggio al gate missione (adozione/portabilità, Principio X), non "bellezza".
- **R-4 — Deriva D↔N:** la tentazione di mettere un LLM nel core per "spiegare/diagnosticare".
  Mitigazione: confine costituzionale esplicito; l'intelligenza sta nell'agente ospite.
- **R-5 — Onestà dei claim (Principio XII):** una guida che dice "fatto" senza verificare. Mitigazione:
  `doctor` come verifica reale; la guida riporta l'esito vero, non presunto.
- **R-6 — Drift dell'auto-documentazione:** la reference "self-describing" che diverge dalla realtà.
  Mitigazione: derivata dai vehicle/asset reali e sottoposta a lint, non scritta a mano una tantum.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Ubiquitous):** *All intelligence in this epic shall live in host-side skills/agents over the
  deterministic vehicles (CLI/MCP); the core shall never call an LLM.*
- **REQ-E2 (Ubiquitous):** *The usability assets (skills, concierge agent, command, hooks, reference)
  shall be host-agnostic and installable on both supported assistants (Claude, Copilot) via the existing
  installer, with a parity guard.*
- **REQ-E3 (Event-driven):** *When setup or a health check is requested, the system shall report a
  deterministic, actionable status (env / provider / index freshness / MCP), naming what is missing and
  how to remediate.*
- **REQ-E4 (Optional):** *Where a usability skill needs runtime state to guide or diagnose, the system
  shall expose that state through a deterministic vehicle signal (the skill shall not rely on internals).*
- **REQ-E5 (Unwanted):** *If a usability flow would otherwise report success without verification, then
  the system shall verify via the deterministic health primitive before claiming success (fail loud,
  Principio XII).*
- **REQ-E6 (Ubiquitous):** *The self-describing documentation shall be consumable both by the host agent
  and by a non-internals human, and shall travel with the install (not require access to the Sertor repo).*

## 8. Backlog di feature

> Cinque pilastri (A–E). L'ordine di valore concordato è **A (1) → B (2) → C (3) → D (4)**, con E
> trasversale. Il **substrato deterministico** (doctor, help, progress) è il prerequisito che rende le
> skill non cieche.

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **`sertor-rag doctor` — verifica di salute deterministica** (env completo? provider raggiungibile? indice presente/fresco? MCP vivo?), esito azionabile. Concretizza il `--check` *deferred* di E2/FEAT-003 | Il "ha funzionato?" che oggi manca; substrato di ogni guida/diagnosi | **Must** | da decomporre |
| FEAT-002 | **guided-setup** — skill (+ ramo del concierge) che conduce install→configure→verify conversando: sceglie il provider dal contesto, riempie `.env` via `configure --set`, lancia `doctor` | Dal nulla a "RAG verificato" senza conoscere gli internals (CS-1) | **Must** | da decomporre |
| FEAT-003 | **Download GloVe con progress/ETA** (deterministico, UX-facing) — assorbe l'ergonomia UX-facing da E2/FEAT-010 | Toglie l'attrito più visibile del primo `index` | **Should** | da decomporre |
| FEAT-004 | **config-recommender** — skill che profila il repo (linguaggi/dimensione/airgapped?/creds cloud?), **consiglia** provider/backend/engine, spiega `backend≠store` e applica via `configure` | Riduce l'attrito decisionale a monte; meno scelte "alla cieca" | **Should** | da decomporre |
| FEAT-005 | **explain / what-is — auto-documentazione dual-audience** — skill + comando che rispondono "cos'è / a cosa serve / cosa aspettarsi / come si usa", grounded su una **reference che viaggia con l'install**; consultabile da agente **e** umano non-interno | Comprensione inline senza internals (CS-4); il tema sollevato dall'utente | **Should** | da decomporre |
| FEAT-006 | **tour / onboarding + help CLI più ricco** — "cosa può fare Sertor in questo repo?" e un help agent-friendly/scopribile | Scoperta delle capacità; adozione | **Could** | da decomporre |
| FEAT-007 | **search-diagnose** — skill "perché non trova X?": incrocia `validate-path` + `search` + osservabilità, interpreta e propone il fix (re-index? provider? soglia? indice stantio/reconnect?) | Sblocca il valore quotidiano quando il retrieval rende male (CS-3) | **Should** | da decomporre |
| FEAT-008 | **`search --explain`** (opzionale) — segnale deterministico per `search-diagnose` (perché un risultato rankа dove rankа) | Rende la diagnosi precisa invece che euristica | **Could** | da decomporre |
| FEAT-009 | **Agente *concierge*** — agente sottile che dispatcha A–D e fa check proattivi; distribuito dual-target | L'esperienza unitaria "a strati" sopra le skill focalizzate | **Should** | da decomporre |

> **Nota sull'MVP:** la prima release utile è **FEAT-001 + FEAT-002** (priorità 1): un `doctor`
> deterministico e una guida che porta a "verificato". Poi config-recommender (2), auto-documentazione &
> scoperta (3), diagnosi d'uso (4). L'agente concierge (E) cresce mano a mano che le skill esistono.

> **Confine ribadito:** i *meccanismi* (observability store/TUI = E3; refresh incrementale + hook
> freschezza = `sertor-core`/E10; packaging/lifecycle/install-kit = E2) **restano** nelle epiche
> d'origine; questa epica li consuma e ne possiede solo l'**esperienza**. Gli `epic.md` d'origine vanno
> annotati con un banner sugli item UX-facing spostati qui.

## 9. Domande aperte
- **DA-U-a — Granularità di `doctor`:** [DA CHIARIRE in decomposizione: un solo comando con sezioni
  (env/provider/index/MCP) o sotto-check selezionabili? Default proposto: un comando con esito
  strutturato + flag opzionali per il singolo check.]
- **DA-U-b — Sede della reference dual-audience:** [DA CHIARIRE: la "self-describing reference" vive
  come asset installato dedicato, si appoggia a `wiki/explainers/` + `claude-md-block`, o entrambi?
  Default proposto: asset installato che riusa/estende gli explainer, così viaggia con l'install.]
- **DA-U-c — Confini del concierge vs skill singole:** [DA CHIARIRE: quanto "spesso" è il concierge —
  puro dispatcher o con check proattivi propri? Default proposto: sottile, dispatcher + pochi check
  proattivi (freschezza/doctor) all'avvio.]
- **DA-U-d — `search --explain` vs osservabilità:** [DA CHIARIRE: il "perché di un rank" è un flag nuovo
  o si ricava dai segnali di osservabilità già esistenti? Da decidere in FEAT-007/008 sui dati reali.]
- **DA-U-e — Promozione degli item da E2/E3/E10:** confermato il modello "owner dell'esperienza +
  cross-ref"; [DA CHIARIRE solo se in decomposizione emergesse un item al confine ambiguo
  esperienza/meccanismo.]
