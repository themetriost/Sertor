# Feature Specification: Parità funzionale completa su Copilot CLI + governance dual-target

**Feature Branch**: `056-parita-asset-copilot`

**Created**: 2026-06-18

**Status**: Draft

**Input**: Deriva da `requirements/debito-tecnico/host-agnosticita-asset-residui/requirements.md`
(decomposizione di FEAT-001 dell'epica `debito-tecnico`). Verifica empirica su host Copilot reale
(Spike, Copilot CLI 1.0.63): la capacità **wiki è non funzionante** su Copilot, nonostante la "parità
funzionale" dichiarata da FEAT-007/009. Due cause accertate: (1) il **payload multi-file** della skill
`wiki-author` (`wiki-playbook.md`, 9 moduli `ops/*.md`, `page-craft.md`/`wiki-craft.md`/`log-craft.md`)
**non viene depositato** dal piano d'installazione Copilot (rende solo `SKILL.md` → custom-agent);
(2) i **body** degli asset distribuiti citano path `.claude/…` e il comando slash `/wiki`, **inesistenti
su Copilot** (il seam traduce il contenitore ma riusa il body verbatim). La guardia esistente verifica il
body byte-identico ma non i path interni né la presenza dei file referenziati → il bug è passato. Le
decisioni di scope D1–D6 e Q1–Q5 sono **già risolte** (2026-06-18); non si riaprono — eventuali ambiguità
di *come* vanno a `/speckit-plan`.

---

> **Confine vincolante (riflesso ovunque in questa spec — non riaprire):** la parità Copilot si ottiene
> **neutralizzando la sorgente** (body host-agnostici, byte-identici Claude↔Copilot) e **depositando il
> payload multi-file** su Copilot in un container dedicato non-agente `.github/sertor/wiki-author/`. I
> body referenziano il payload **per nome di file** (host-agnostico), mai per path assoluto (i due host
> hanno container diversi). Si **riusa l'infrastruttura** (`iter_asset_dir` + byte-copy) senza nuovi
> `Surface`/`ArtifactKind`. Il **ramo Claude resta invariato** (non-regressione, gate) e la **guardia
> byte-identica esistente resta verde**. Ambito = tutti gli asset distribuibili (wiki + governance
> `requirements` + rag). `install ≠ run`. `sertor-flow` resta senza dipendenza da `sertor-core`/`sertor`.
> Copilot = **copilot-cli** (VS Code già rimosso, FEAT-012).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - La wiki funziona su Copilot CLI (Priority: P1)

Un utente con host Copilot CLI installa la capacità wiki e invoca l'agente wiki. Oggi la sua **prima
azione** — leggere il playbook (la "fonte unica" del sistema wiki) — fallisce, perché il playbook e i
suoi moduli di supporto non sono stati depositati e l'istruzione punta a un path `.claude/` che su quel
host non esiste. Con questa storia il payload completo della skill è presente sull'host e l'agente
**esegue con successo** la lettura del playbook e dei suoi moduli.

**Why this priority**: È il valore terminale della feature e la causa-radice del bug verificato sul
campo. Senza il payload e senza un riferimento risolvibile, la capacità wiki su Copilot è completamente
non funzionante (non degradata): l'agente carica ma fallisce alla prima istruzione.

**Independent Test**: Installare la capacità wiki con il target Copilot CLI in una dir pulita e
verificare che il file del playbook e i moduli di supporto esistano nel container dedicato; poi seguire
il riferimento dal body dell'agente al playbook e dai moduli interni del playbook ai loro vicini,
verificando che ogni file referenziato esista.

**Acceptance Scenarios**:

1. **Given** un'installazione della capacità wiki con il target Copilot CLI, **When** si ispezionano gli
   artefatti, **Then** il file del playbook e tutti i moduli di supporto della skill (`ops/*`, craft)
   sono presenti nel container dedicato, con la struttura preservata.
2. **Given** il body dell'agente/skill wiki reso per Copilot, **When** se ne segue il riferimento al
   playbook, **Then** il file referenziato esiste tra gli artefatti depositati.
3. **Given** il playbook depositato per Copilot, **When** se ne seguono i link interni (moduli di
   operazione e pagine di craft), **Then** ogni file referenziato esiste nel container.

---

### User Story 2 - Zero riferimenti Claude sull'host Copilot (Priority: P1)

Un utente Copilot non deve trovare, in nessun artefatto reso per il suo host, riferimenti a percorsi
`.claude/`, comandi slash (`/wiki`, …) o nomi di assistente che sul suo host non esistono. Con questa
storia ogni body distribuito è host-agnostico: si riferisce al payload per nome di file e descrive le
operazioni in modo capability-neutro.

**Why this priority**: Anche con il payload presente, un riferimento `.claude/` letterale o un comando
slash inesistente porterebbe l'agente fuori strada. La neutralità del body è la precondizione del riuso
verbatim (fonte unica) e del funzionamento su entrambi gli host.

**Independent Test**: Rendere il piano d'installazione Copilot e scandire ogni file reso, verificando
l'assenza di occorrenze `.claude/`, di comandi slash come invocazione e di nomi di assistente.

**Acceptance Scenarios**:

1. **Given** il piano d'installazione Copilot reso, **When** si scandiscono i file prodotti, **Then**
   nessuno contiene la stringa di percorso `.claude/`.
2. **Given** gli stessi file, **When** si cercano comandi slash come modo d'invocazione, **Then** non ve
   ne sono.
3. **Given** lo stesso body reso per Claude e per Copilot, **When** se ne confronta il contenuto,
   **Then** è byte-identico (la neutralizzazione preserva la fonte unica).

---

### User Story 3 - Parità su tutte le superfici distribuibili (Priority: P2)

Le stesse garanzie (payload completo dove serve, body host-agnostici) valgono non solo per la wiki ma
per **tutte** le superfici distribuibili: la governance (skill `requirements` e agenti) e il rag. Con
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
oppure cita un file che non è stato depositato (**closure dei riferimenti**). La stessa closure è
verificata anche sul ramo Claude, così la neutralizzazione non rompe il dogfood.

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
   host-agnostico (no path d'assistente letterali, no slash, riferimento-per-nome).
2. **Given** la pagina di targeting degli assistenti, **When** la si consulta, **Then** documenta la
   parità "by construction" e indica la guardia come enforcement.
3. **Given** il blocco rituale distribuito, **When** lo si consulta, **Then** include una voce di
   Definition of Done che lega la modifica di un asset distribuibile alla verifica di parità.

---

### Edge Cases

- **Body byte-identico ma payload in path diversi per host** → il body non può contenere un path
  assoluto valido per entrambi; si referenzia il payload **per nome di file** e l'agente lo localizza
  (nome univoco, reperibile). [risolve la tensione D1×D2]
- **File di supporto con frontmatter** → un futuro file di payload con frontmatter, byte-copiato,
  resterebbe in formato Claude; la guardia di parità scandisce **anche** i file di supporto resi.
- **Falso positivo della guardia slash** → distinguere `/wiki` (comando) da `wiki/` (path POSIX) o da
  una URL: il controllo cerca lo slash-comando in contesto istruzionale, con test-del-test sui casi noti.
- **Riferimento dangling introdotto da un refactor** → la closure dei riferimenti (su entrambi i piani)
  lo intercetta nominando il file mancante.
- **Container `.github/sertor/` interpretato come area di agent-discovery** → scelto apposta fuori da
  `.github/agents/`; se il client lo scandisse per agenti, il fallback è un altro container non-agente
  con riferimento-per-nome aggiornato (validazione empirica su host reale).
- **Host Copilot già installato** → riceve il fix ri-eseguendo l'aggiornamento dell'installazione
  (`upgrade`), non con una migrazione speciale.
- **Tentazione di tradurre i path nel body per-target** → esclusa: violerebbe la fonte unica
  byte-identica; la via scelta è neutralizzare la sorgente.

## Requirements *(mandatory)*

> **Parità per costruzione:** ogni asset distribuibile è host-agnostico alla sorgente (body byte-identici)
> e il suo payload è depositato dove ciascun host lo cerca; una guardia offline con closure dei
> riferimenti attesta che nessun riferimento Claude o dangling sopravviva. Il ramo Claude è invariato.

### Functional Requirements

**Gruppo A — Deposito del payload multi-file su Copilot**

- **FR-001**: Quando si installa la capacità wiki con il target Copilot CLI, il sistema MUST depositare
  l'intero payload di supporto della skill `wiki-author` (playbook, moduli di operazione, pagine di
  craft) in un container dedicato non-agente, preservando la struttura relativa.
- **FR-002**: Il sistema MUST copiare i file di supporto **byte-per-byte** (sono documenti senza
  frontmatter, non resi come custom-agent).
- **FR-003**: Il payload depositato per Copilot MUST provenire dalla **stessa fonte unica** degli asset
  Claude, enumerata dinamicamente (nessuna lista hardcoded dei file).
- **FR-004**: La dichiarazione dei path di proprietà del piano Copilot MUST includere il container del
  payload, così che disinstallazione e aggiornamento lo rimuovano/aggiornino in blocco.

**Gruppo B — Neutralizzazione dei body (host-agnostici, byte-identici)**

- **FR-005**: Gli asset sorgente distribuibili MUST NOT contenere path d'assistente letterali (`.claude/`)
  nei body; i riferimenti al payload MUST essere espressi **per nome di file**, host-agnostici.
- **FR-006**: Gli asset sorgente distribuibili MUST NOT citare comandi slash come modo d'invocazione;
  MUST usare linguaggio capability-neutro.
- **FR-007**: Gli asset sorgente distribuibili SHOULD NOT contenere nomi di assistente ("Claude Code") in
  contesto istruzionale LLM-facing.
- **FR-008**: Dopo la neutralizzazione, il body reso per Claude e per Copilot MUST restare
  **byte-identico** (la guardia byte-identica esistente resta verde).
- **FR-009**: La neutralizzazione MUST applicarsi a **tutte** le superfici distribuibili: wiki,
  governance (skill `requirements` e agenti), rag.

**Gruppo C — Guardia di parità offline**

- **FR-010**: Una suite offline MUST rendere i piani Copilot (wiki + governance + rag) e verificare, per
  ogni file reso, l'**assenza** della stringa di percorso `.claude/`.
- **FR-011**: La suite MUST verificare l'assenza di comandi slash come invocazione nei file resi per
  Copilot.
- **FR-012**: La suite SHOULD verificare l'assenza di nomi di assistente ("Claude Code") nei body resi.
- **FR-013**: La suite MUST verificare la **closure dei riferimenti**: ogni file citato da un body reso
  MUST essere presente tra i target del piano (risolvendo i relativi rispetto al container del referente).
- **FR-014**: Il controllo di closure SHOULD essere eseguito **anche sul piano Claude**, per attestare
  che la neutralizzazione non abbia introdotto riferimenti dangling nel ramo dogfood.

**Gruppo D — Governance dual-target**

- **FR-015**: Il playbook del wiki SHOULD contenere una sezione di authoring host-agnostico che codifichi
  FR-005/006/007 e la regola del riferimento-per-nome.
- **FR-016**: La pagina di targeting degli assistenti SHOULD documentare la parità "by construction" (il
  *come*) e indicare la guardia di parità come enforcement.
- **FR-017**: Il blocco rituale distribuibile SHOULD includere una voce di Definition of Done: toccare un
  asset distribuibile richiede la verifica di parità Claude↔Copilot.
- **FR-018**: Il dogfood di questo repository (gli asset `.claude/**` derivati e il file di istruzioni)
  SHOULD essere ri-sincronizzato con gli asset neutralizzati (coerenza dogfood↔asset).

**Gruppo E — Non-regressione**

- **FR-019**: Il ramo d'installazione Claude MUST restare invariato e produrre artefatti funzionalmente
  equivalenti a prima del refactor; i body neutralizzati MUST restare validi su Claude (il riferimento
  per nome risolve al payload depositato accanto alla skill).

### Key Entities

- **Payload di supporto della skill**: l'insieme dei documenti che la skill wiki legge a runtime
  (playbook + moduli di operazione + pagine di craft), oggi depositato solo su Claude.
- **Container del payload (per host)**: la sede del payload su ciascun host — l'albero skill di Claude
  per Claude, un container dedicato non-agente per Copilot — con struttura preservata.
- **Body host-agnostico**: il contenuto istruzionale di skill/agente/comando, neutralizzato (nessun path
  d'assistente letterale, nessun comando slash, riferimento al payload per nome), byte-identico su
  entrambi gli host.
- **Riferimento-per-nome**: la forma host-agnostica con cui un body indica un file del payload (per nome,
  non per path assoluto), risolvibile dall'agente su entrambi gli host.
- **Guardia di parità**: la suite offline che rende i piani Copilot (e Claude per la closure) e attesta
  assenza di riferimenti Claude e assenza di riferimenti dangling.
- **Closure dei riferimenti**: l'invariante secondo cui ogni file citato da un body reso esiste tra gli
  artefatti depositati dal piano.
- **Sedi di governance dual-target**: le tre sedi (playbook, pagina di targeting, blocco rituale/DoD) che
  codificano la regola di authoring host-agnostico.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (payload presente su Copilot)**: dopo l'installazione wiki con `copilot-cli`, il playbook e
  **tutti** i moduli di supporto esistono nel container dedicato (oggi: **0** depositati).
- **SC-002 (zero `.claude/` su Copilot)**: nei file resi per Copilot (tutti gli installer), in **0** casi
  compare la stringa di percorso `.claude/`.
- **SC-003 (zero slash-command su Copilot)**: nei file resi per Copilot, in **0** casi compare un comando
  slash come invocazione.
- **SC-004 (closure verde)**: sul piano Copilot **e** sul piano Claude, in **0** casi un body cita un file
  non depositato (riferimenti dangling = 0).
- **SC-005 (non-regressione Claude)**: gli artefatti per `claude` sono funzionalmente equivalenti prima e
  dopo, e la guardia byte-identica + la suite Claude restano verdi senza modifiche alla loro logica.
- **SC-006 (link interni risolti)**: i link relativi interni del payload risolvono nel container Copilot.
- **SC-007 (governance dual-target presente)**: la regola di authoring host-agnostico è presente in tutte
  e tre le sedi.
- **SC-008 (verifica empirica su host reale)**: invocando l'agente wiki su Copilot CLI 1.0.63 (Spike), la
  **prima azione** (lettura del playbook) **riesce**; e il container `.github/sertor/` **non** genera
  agenti-fantasma.

## Assumptions

- **Le decisioni D1–D6 e Q1–Q5 sono risolte a monte** (requirements, 2026-06-18) e codificate qui:
  neutralizzare la sorgente (non tradurre per-target, D1); container dedicato `.github/sertor/wiki-author/`
  (D2); riuso `iter_asset_dir`+byte-copy senza nuovi `Surface`/`ArtifactKind` (D3); guardia di parità con
  closure (D4); governance in tre sedi (D5); full sweep wiki+governance+rag (D6); riferimento-per-nome per
  i body byte-identici. Non si riaprono: le ambiguità di *come* sono di pertinenza di `/speckit-plan`.
- **[ASSUNTO] A-1 — file di supporto senza frontmatter**: i documenti del payload sono `.md` puri letti a
  runtime; il byte-copy è corretto. Da confermare in audit; se un file avesse frontmatter, la guardia lo
  espone.
- **[ASSUNTO] A-2 — localizzazione per nome**: un agente LLM su Copilot CLI localizza un file di payload
  citato per nome univoco (lettura/ricerca), senza un path assoluto.
- **[ASSUNTO] A-3 — host reale disponibile**: Spike è disponibile come host Copilot CLI reale per la
  verifica empirica pre-merge (SC-008).
- **[ASSUNTO] A-4 — container non-agente**: `.github/sertor/` non è interpretato dal client Copilot come
  area di agent-discovery. Da confermare empiricamente (SC-008); fallback = altro container non-agente.
- **Confine del refactor**: confinato ai pacchetti installer e ai loro asset (`sertor`, `sertor-flow`,
  `sertor-install-kit`). **`sertor-core` resta invariato**; il toolkit condiviso resta privo di dipendenze
  dal nucleo; `sertor-flow` resta senza dipendenza da `sertor-core`/`sertor`.
- **Anti-drift preservato**: i body restano byte-identici fra Claude e Copilot (solo neutralizzati); non
  si introducono copie mantenute separatamente per Copilot.
- **`install ≠ run`**: non distruttivo, idempotente; uninstall rimuove il container del payload in blocco.
- **Host già installati**: ricevono il fix via aggiornamento dell'installazione (`upgrade`), non con una
  migrazione dedicata.
- **Fuori ambito (asse diverso / capacità future)**: commenti "Claude Code" negli **script** `.ps1` (non
  body LLM-facing); rinomina `copilot-cli`→`copilot` (E10-FEAT-007); **promozione di `derive-entity-types`**
  a capacità di produzione (prototipo-coupled → backlog separato); eventuali payload RAG residui scoperti
  in audit (follow-up nella stessa FEAT-001 se trovati).
- **Domande di design aperte (→ `/speckit-plan`, non bloccano la spec)**: la forma esatta del
  riferimento-per-nome nei body; la collocazione precisa del container e del loop di deposito nel
  plan-builder; la forma della regex anti-slash della guardia; la collocazione delle tre sedi di
  governance. Sono ambiguità di *come*, non di *cosa/perché*.
