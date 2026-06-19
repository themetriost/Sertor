# Feature Specification: Parità funzionale completa su Copilot CLI + governance dual-target

**Feature Branch**: `056-parita-asset-copilot`

**Created**: 2026-06-18 · **Revised**: 2026-06-19 (meccanismo nativo agent-skills)

**Status**: Draft

**Input**: Deriva da `requirements/debito-tecnico/host-agnosticita-asset-residui/requirements.md`
(decomposizione di FEAT-001 dell'epica `debito-tecnico`). Verifica empirica su host Copilot reale
(Spike, Copilot CLI 1.0.63): la capacità **wiki è non funzionante** su Copilot, nonostante la "parità
funzionale" dichiarata da FEAT-007/009. Due cause accertate: (1) il **payload multi-file** della skill
`wiki-author` (`wiki-playbook.md`, 9 moduli `ops/*.md`, `page-craft.md`/`wiki-craft.md`/`log-craft.md`)
**non viene depositato** dal piano d'installazione Copilot; (2) i **body** degli asset distribuiti citano
path `.claude/…` e il comando slash `/wiki`, **inesistenti su Copilot**.

> **Revisione 2026-06-19 — meccanismo NATIVO.** Una prima implementazione (commit `b6e85b7`) aveva
> appiattito la skill in un **custom-agent** + container `.github/sertor/` + placeholder `{SKILL_DIR}`.
> Letta la **documentazione ufficiale Copilot** (docs.github.com/copilot CLI «add-skills»), questo è una
> **reinvenzione** del meccanismo nativo: Copilot ha le **agent skills native** (cartelle `.github/skills/`,
> `.claude/skills/`, `.agents/skills/`) e **auto-scopre tutti i file della cartella della skill**
> (incluse sotto-cartelle come `ops/`). Il redesign usa il meccanismo nativo. Le decisioni di scope
> D1/D4/D5/D6 restano; **D2/D3 sono corrette** (vedi requirements §3).

---

> **Confine vincolante (riflesso ovunque in questa spec — non riaprire):** la capacità wiki su Copilot è
> **una sola skill NATIVA** depositata in `.github/skills/wiki-author/**` (`SKILL.md` + payload
> auto-scoperto). La skill **assorbe il ruolo del command `/wiki`**: il suo `SKILL.md` è il dispatcher
> delle 8 operazioni (corpo derivato dalla fonte unica `commands/wiki.md`), perché su Copilot una skill
> nativa è già user-invocabile (`/skills`) e model-invocabile e **non esistono slash-command custom**. I
> **body** sono neutralizzati alla sorgente (no `.claude/` letterale, no slash-command come invocazione,
> no nomi d'assistente, no `$ARGUMENTS`); il **payload** (playbook/ops/craft) è byte-copiato e
> **byte-identico** Claude↔Copilot. I riferimenti interni restano **relativi** e risolvono identici grazie
> alla co-locazione (container paralleli `.claude/skills/wiki-author/` ↔ `.github/skills/wiki-author/`).
> Si **riusa l'infrastruttura** (`iter_asset_dir` + byte-copy) senza nuovi `ArtifactKind`; si **rimuovono**
> il render skill→custom-agent e il placeholder `{SKILL_DIR}`. Il **ramo Claude resta invariato**
> (non-regressione, gate). Ambito = tutti gli asset distribuibili (wiki + governance `requirements` +
> rag). `install ≠ run`. `sertor-flow` resta senza dipendenza da `sertor-core`/`sertor`. Copilot =
> **copilot-cli** (VS Code già rimosso, FEAT-012).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - La wiki funziona su Copilot CLI (Priority: P1)

Un utente con host Copilot CLI installa la capacità wiki e invoca la skill wiki. Oggi la sua **prima
azione** — leggere il playbook (la "fonte unica" del sistema wiki) — fallisce, perché il playbook e i
suoi moduli di supporto non sono stati depositati e l'istruzione punta a un path `.claude/` che su quel
host non esiste. Con questa storia la skill nativa completa è presente sull'host, Copilot la auto-scopre,
e l'agente **esegue con successo** la lettura del playbook e dei suoi moduli co-locati.

**Why this priority**: È il valore terminale della feature e la causa-radice del bug verificato sul
campo. Senza la skill nativa e i suoi file co-locati, la capacità wiki su Copilot è completamente non
funzionante (non degradata): l'agente carica ma fallisce alla prima istruzione.

**Independent Test**: Installare la capacità wiki con il target Copilot CLI in una dir pulita e
verificare che `.github/skills/wiki-author/` contenga `SKILL.md` (dispatcher) + il playbook + i moduli
`ops/*` + le pagine craft; poi seguire il riferimento dal `SKILL.md` al playbook e dai moduli interni del
playbook ai loro vicini, verificando che ogni file referenziato esista nella cartella skill.

**Acceptance Scenarios**:

1. **Given** un'installazione della capacità wiki con il target Copilot CLI, **When** si ispezionano gli
   artefatti, **Then** `.github/skills/wiki-author/` contiene `SKILL.md` e tutti i file di payload della
   skill (`wiki-playbook.md`, `ops/*`, `*-craft.md`), con la struttura preservata.
2. **Given** il `SKILL.md` Copilot, **When** se ne segue il riferimento al playbook, **Then** il file
   referenziato esiste nella cartella skill (co-locato).
3. **Given** il playbook depositato per Copilot, **When** se ne seguono i link interni (moduli di
   operazione e pagine di craft), **Then** ogni file referenziato esiste nella cartella skill.

---

### User Story 2 - Zero riferimenti Claude sull'host Copilot (Priority: P1)

Un utente Copilot non deve trovare, in nessun artefatto reso per il suo host, riferimenti a percorsi
`.claude/`, comandi slash (`/wiki`, …), nomi di assistente o token (`$ARGUMENTS`) che sul suo host non
esistono. Con questa storia ogni body distribuito è host-agnostico: si riferisce al payload con
riferimenti relativi co-locati e descrive le operazioni in modo capability-neutro.

**Why this priority**: Anche con la skill presente, un riferimento `.claude/` letterale o un comando
slash inesistente porterebbe l'agente fuori strada. La neutralità del body è la precondizione del
funzionamento su entrambi gli host.

**Independent Test**: Rendere il piano d'installazione Copilot e scandire ogni file reso, verificando
l'assenza di occorrenze `.claude/`, di comandi slash come invocazione, di nomi di assistente e di
`$ARGUMENTS`.

**Acceptance Scenarios**:

1. **Given** il piano d'installazione Copilot reso, **When** si scandiscono i file prodotti, **Then**
   nessuno contiene la stringa di percorso `.claude/`.
2. **Given** gli stessi file, **When** si cercano comandi slash come modo d'invocazione, **Then** non ve
   ne sono.
3. **Given** i file di payload (playbook/ops/craft), **When** se ne confronta il contenuto col deposito
   Claude, **Then** sono byte-identici (byte-copiati dalla stessa fonte unica).

---

### User Story 3 - Parità su tutte le superfici distribuibili (Priority: P2)

Le stesse garanzie (skill/payload completi dove serve, body host-agnostici) valgono non solo per la wiki
ma per **tutte** le superfici distribuibili: la governance (skill `requirements` e agenti) e il rag. Con
questa storia un audit completo (full sweep) neutralizza ogni riferimento Claude ovunque e copre ogni
payload eventualmente multi-file.

**Why this priority**: "Tutto deve essere accessibile su Copilot": una parità parziale lascerebbe altre
superfici con lo stesso difetto latente. È P2 perché segue il fix del caso verificato (wiki, P1) ma
completa il "done".

**Independent Test**: Rendere i piani Copilot di governance e rag e applicare gli stessi controlli di
US2 (zero `.claude/`, zero slash) e di US1 (closure dei riferimenti) a quei piani.

**Acceptance Scenarios**:

1. **Given** il piano Copilot della governance, **When** lo si scandisce, **Then** nessun body reso
   contiene `.claude/` o comandi slash, e ogni file referenziato è depositato.
2. **Given** il piano Copilot del rag, **When** lo si scandisce, **Then** valgono le stesse assenze e la
   stessa closure.

---

### User Story 4 - Una guardia rende la regressione impossibile (Priority: P2)

Un manutentore modifica un asset distribuibile. Con questa storia una guardia offline fallisce se un
asset reso per Copilot reintroduce un riferimento `.claude/`, un comando slash, un nome di assistente,
un `$ARGUMENTS`, oppure cita un file che non è stato depositato (**closure dei riferimenti**). La stessa
closure è verificata anche sul ramo Claude, così la neutralizzazione non rompe il dogfood.

**Why this priority**: Il bug originale è passato perché la guardia esistente non verificava i path
interni né l'esistenza dei file referenziati. Senza questa guardia il difetto può rientrare silenzioso.
È P2 perché protegge le storie P1 nel tempo.

**Independent Test**: Eseguire la suite della guardia di parità su un albero asset pulito (PASS), poi
reintrodurre deliberatamente un riferimento `.claude/` o un riferimento dangling in un asset e
verificare che almeno un controllo fallisca.

**Acceptance Scenarios**:

1. **Given** la suite di parità su asset corretti, **When** la si esegue, **Then** passa.
2. **Given** un asset in cui sia reintrodotto un path `.claude/` o un comando slash reso per Copilot,
   **When** si esegue la suite, **Then** almeno un controllo fallisce.
3. **Given** un body che cita un file non presente tra i target del piano, **When** si esegue il
   controllo di closure (su piano Copilot **e** Claude), **Then** fallisce nominando il riferimento
   dangling.

---

### User Story 5 - Dual-target by construction (Priority: P3)

Un manutentore che scrive un nuovo asset host-facing deve sapere, dal processo stesso, che l'asset nasce
host-agnostico. Con questa storia la regola è codificata in tre sedi coordinate (il playbook del wiki, la
pagina di targeting degli assistenti, e il blocco rituale distribuito come Definition of Done), così la
parità non dipende dalla memoria del singolo.

**Why this priority**: È la prevenzione strutturale del problema. È P3 perché è governance (non sblocca
una capacità rotta) ma è ciò che impedisce il ripetersi del difetto.

**Independent Test**: Ispezionare le tre sedi e verificare che ciascuna contenga la regola di authoring
host-agnostico e il riferimento alla guardia come enforcement.

**Acceptance Scenarios**:

1. **Given** il playbook del wiki, **When** lo si consulta, **Then** contiene una sezione di authoring
   host-agnostico (no path d'assistente letterali, no slash, riferimenti relativi co-locati).
2. **Given** la pagina di targeting degli assistenti, **When** la si consulta, **Then** documenta la
   parità "by construction" (skill native per-host) e indica la guardia come enforcement.
3. **Given** il blocco rituale distribuito, **When** lo si consulta, **Then** include una voce di
   Definition of Done che lega la modifica di un asset distribuibile alla verifica di parità.

---

### Edge Cases

- **Command `/wiki` assente su Copilot** → su Copilot non esistono slash-command custom; il ruolo del
  command (dispatcher 8-operazioni) è **assorbito** dal `SKILL.md` della skill nativa, invocabile via
  `/skills` o per menzione naturale. [risolve la mancanza del veicolo command]
- **SKILL.md divergente per host** → il `SKILL.md` Claude (autore) e quello Copilot (dispatcher) hanno
  corpi diversi ma **fonte unica** (`commands/wiki.md` per il dispatcher); il payload resta byte-identico.
  La guardia byte-identica si applica alle superfici ancora rese custom-agent (`wiki-curator`).
- **File di supporto con frontmatter** → un futuro file di payload con frontmatter, byte-copiato,
  resterebbe in formato Claude; la guardia di parità scandisce **anche** i file di supporto resi.
- **Falso positivo della guardia slash** → distinguere `/wiki` (comando) da `wiki/` (path POSIX) o da
  una URL: il controllo cerca lo slash-comando in contesto istruzionale, con test-del-test sui casi noti.
- **Riferimento dangling introdotto da un refactor** → la closure dei riferimenti (su entrambi i piani)
  lo intercetta nominando il file mancante.
- **Host Copilot già installato** → riceve il fix ri-eseguendo l'aggiornamento dell'installazione
  (`upgrade`), non con una migrazione speciale.
- **Tentazione di tradurre i path nel body per-target** → esclusa: i riferimenti restano relativi
  co-locati, validi su entrambi gli host senza traduzione per-target.

## Requirements *(mandatory)*

> **Parità per costruzione:** ogni asset distribuibile è host-agnostico alla sorgente (body neutralizzati)
> e la skill wiki è depositata come **skill nativa** dove ciascun host la cerca; una guardia offline con
> closure dei riferimenti attesta che nessun riferimento Claude o dangling sopravviva. Il ramo Claude è
> invariato.

### Functional Requirements

**Gruppo A — Deposito della skill nativa su Copilot**

- **FR-001**: Quando si installa la capacità wiki con il target Copilot CLI, il sistema MUST depositare
  la skill `wiki-author` come **skill nativa** sotto `.github/skills/wiki-author/` (`SKILL.md` + payload
  playbook/ops/craft), preservando la struttura relativa, così che il client la auto-scopra.
- **FR-002**: Il `SKILL.md` reso per Copilot MUST essere il **dispatcher delle 8 operazioni** (corpo
  derivato dalla fonte unica `commands/wiki.md`, neutralizzato) con frontmatter nativo
  (`name`/`description`); i file di payload MUST essere copiati **byte-per-byte** dagli asset canonici.
- **FR-003**: L'albero skill depositato per Copilot MUST provenire dalla **stessa fonte unica** degli
  asset Claude, enumerata dinamicamente (nessuna lista hardcoded dei file).
- **FR-004**: La dichiarazione dei path di proprietà del piano Copilot MUST includere la cartella skill
  `.github/skills/wiki-author`, così che disinstallazione e aggiornamento la rimuovano/aggiornino in
  blocco; il render skill→custom-agent e il container `.github/sertor/` NON MUST più essere prodotti.

**Gruppo B — Neutralizzazione dei body (host-agnostici)**

- **FR-005**: Gli asset sorgente distribuibili MUST NOT contenere path d'assistente letterali (`.claude/`)
  nei body; i riferimenti al payload MUST essere **relativi** (co-locati), host-agnostici.
- **FR-006**: Gli asset sorgente distribuibili MUST NOT citare comandi slash come modo d'invocazione né
  token `$ARGUMENTS`; MUST usare linguaggio capability-neutro.
- **FR-007**: Gli asset sorgente distribuibili SHOULD NOT contenere nomi di assistente ("Claude Code") in
  contesto istruzionale LLM-facing.
- **FR-008**: I **file di payload** (playbook/ops/craft) MUST restare **byte-identici** tra deposito
  Claude e deposito Copilot (byte-copiati dalla stessa fonte). Il `SKILL.md` Copilot (dispatcher) deriva
  da `commands/wiki.md` e può divergere dal `SKILL.md` Claude (autore).
- **FR-009**: La neutralizzazione MUST applicarsi a **tutte** le superfici distribuibili: wiki,
  governance (skill `requirements` e agenti), rag.

**Gruppo C — Guardia di parità offline**

- **FR-010**: Una suite offline MUST rendere i piani Copilot (wiki + governance + rag) e verificare, per
  ogni file reso, l'**assenza** della stringa di percorso `.claude/`.
- **FR-011**: La suite MUST verificare l'assenza di comandi slash come invocazione (e di `$ARGUMENTS`)
  nei file resi per Copilot.
- **FR-012**: La suite SHOULD verificare l'assenza di nomi di assistente ("Claude Code") nei body resi.
- **FR-013**: La suite MUST verificare la **closure dei riferimenti**: ogni file citato da un body reso
  MUST essere presente tra i target del piano (risolvendo i relativi rispetto alla cartella del referente).
- **FR-014**: Il controllo di closure SHOULD essere eseguito **anche sul piano Claude**, per attestare
  che la neutralizzazione non abbia introdotto riferimenti dangling nel ramo dogfood.

**Gruppo D — Governance dual-target**

- **FR-015**: Il playbook del wiki SHOULD contenere una sezione di authoring host-agnostico che codifichi
  FR-005/006/007 e la regola dei riferimenti relativi co-locati.
- **FR-016**: La pagina di targeting degli assistenti SHOULD documentare la parità "by construction"
  (skill native per-host, contenitore tradotto) e indicare la guardia di parità come enforcement.
- **FR-017**: Il blocco rituale distribuibile SHOULD includere una voce di Definition of Done: toccare un
  asset distribuibile richiede la verifica di parità Claude↔Copilot.
- **FR-018**: Il dogfood di questo repository (gli asset `.claude/**` derivati e il file di istruzioni)
  SHOULD essere ri-sincronizzato con gli asset neutralizzati (coerenza dogfood↔asset).

**Gruppo E — Non-regressione**

- **FR-019**: Il ramo d'installazione Claude MUST restare invariato e produrre artefatti funzionalmente
  equivalenti a prima del refactor; i body neutralizzati MUST restare validi su Claude (i riferimenti
  relativi risolvono al payload co-locato nella cartella skill).

### Key Entities

- **Skill nativa (per host)**: la cartella skill auto-scoperta dall'assistente — `.claude/skills/wiki-author/`
  su Claude, `.github/skills/wiki-author/` su Copilot — contenente `SKILL.md` + payload, con struttura
  preservata. Su Copilot è **una sola** skill che assorbe anche il dispatcher del command.
- **Payload di supporto della skill**: l'insieme dei documenti che la skill wiki legge a runtime
  (playbook + moduli di operazione + pagine di craft), co-locato con `SKILL.md`, byte-identico fra host.
- **Body host-agnostico**: il contenuto istruzionale, neutralizzato (nessun path d'assistente letterale,
  nessun comando slash/`$ARGUMENTS`, riferimenti relativi co-locati).
- **Dispatcher (SKILL.md Copilot)**: il `SKILL.md` della skill nativa Copilot, derivato dalla fonte unica
  `commands/wiki.md`, che instrada le 8 operazioni del wiki.
- **Guardia di parità**: la suite offline che rende i piani Copilot (e Claude per la closure) e attesta
  assenza di riferimenti Claude e assenza di riferimenti dangling.
- **Closure dei riferimenti**: l'invariante secondo cui ogni file citato da un body reso esiste tra gli
  artefatti depositati dal piano.
- **Sedi di governance dual-target**: le tre sedi (playbook, pagina di targeting, blocco rituale/DoD) che
  codificano la regola di authoring host-agnostico.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (skill presente su Copilot)**: dopo l'installazione wiki con `copilot-cli`,
  `.github/skills/wiki-author/` contiene `SKILL.md` e **tutti** i file di payload (oggi: **0** depositati).
- **SC-002 (zero `.claude/` su Copilot)**: nei file resi per Copilot (tutti gli installer), in **0** casi
  compare la stringa di percorso `.claude/`.
- **SC-003 (zero slash-command / `$ARGUMENTS` su Copilot)**: nei file resi per Copilot, in **0** casi
  compare un comando slash come invocazione o un token `$ARGUMENTS`.
- **SC-004 (closure verde)**: sul piano Copilot **e** sul piano Claude, in **0** casi un body cita un file
  non depositato (riferimenti dangling = 0).
- **SC-005 (non-regressione Claude)**: gli artefatti per `claude` sono funzionalmente equivalenti prima e
  dopo, e la guardia byte-identica + la suite Claude restano verdi senza modifiche alla loro logica.
- **SC-006 (link interni risolti)**: i link relativi interni della skill (SKILL.md→playbook,
  playbook→ops/craft) risolvono nella cartella skill Copilot.
- **SC-007 (governance dual-target presente)**: la regola di authoring host-agnostico è presente in tutte
  e tre le sedi.
- **SC-008 (verifica empirica su host reale)**: `/skills` su Copilot CLI 1.0.63 (Spike) mostra la skill
  `wiki-author`; invocandola, la **prima azione** (lettura del playbook co-locato) **riesce**.

## Assumptions

- **Le decisioni di scope D1/D4/D5/D6 sono risolte a monte** (requirements, 2026-06-18) e restano;
  **D2/D3 corrette il 2026-06-19** sui doc ufficiali: skill nativa `.github/skills/wiki-author/` (D2),
  riuso `iter_asset_dir`+byte-copy senza render custom-agent né `{SKILL_DIR}` (D3). Le ambiguità di *come*
  sono di pertinenza di `/speckit-plan`.
- **[ASSUNTO] A-1 — file di supporto senza frontmatter**: i documenti del payload sono `.md` puri letti a
  runtime; il byte-copy è corretto. Da confermare in audit; se un file avesse frontmatter, la guardia lo
  espone.
- **[ASSUNTO] A-2 — auto-discovery nativa**: Copilot CLI auto-scopre i file della cartella skill
  `.github/skills/wiki-author/` (documentato); la verifica empirica (SC-008) lo conferma sul campo.
- **[ASSUNTO] A-3 — host reale disponibile**: Spike è disponibile come host Copilot CLI reale per la
  verifica empirica pre-merge (SC-008).
- **Confine del refactor**: confinato ai pacchetti installer e ai loro asset (`sertor`, `sertor-flow`,
  `sertor-install-kit`). **`sertor-core` resta invariato**; il toolkit condiviso resta privo di dipendenze
  dal nucleo; `sertor-flow` resta senza dipendenza da `sertor-core`/`sertor`.
- **Fonte unica preservata**: il payload resta byte-identico fra Claude e Copilot (byte-copiato); il
  `SKILL.md` Copilot deriva dalla fonte unica `commands/wiki.md`. Nessuna copia mantenuta separatamente.
- **`install ≠ run`**: non distruttivo, idempotente; uninstall rimuove la cartella skill in blocco.
- **Host già installati**: ricevono il fix via aggiornamento dell'installazione (`upgrade`), non con una
  migrazione dedicata.
- **Fuori ambito (asse diverso / capacità future)**: commenti "Claude Code" negli **script** `.ps1` (non
  body LLM-facing); rinomina `copilot-cli`→`copilot` (E10-FEAT-007); **promozione di `derive-entity-types`**
  a capacità di produzione (prototipo-coupled → backlog separato); eventuali payload RAG residui scoperti
  in audit (follow-up nella stessa FEAT-001 se trovati).
- **Domande di design aperte (→ `/speckit-plan`, non bloccano la spec)**: il frontmatter esatto del
  `SKILL.md` Copilot (dispatcher); la collocazione del loop di deposito nel plan-builder; la forma della
  regex anti-slash della guardia; la collocazione delle tre sedi di governance. Sono ambiguità di *come*.
