# Feature Specification: Pulizia stile delle skill distribuite (ALL-CAPS → imperativo, dedup, ToC, wikilink orfano) (E10-FEAT-022)

**Feature Branch**: `080-pulizia-stile-skill` · **Created**: 2026-06-30 · **Status**: Draft

<!-- Deriva da: FEAT-022 (epica debito-tecnico E10) — requirements/debito-tecnico/pulizia-stile-skill/requirements.md (audit asset first-party 2026-06-26, ISSUE-08) -->

**Input**: FEAT-022 dell'epica `debito-tecnico` (E10). Gli asset **skill** che Sertor deposita sugli
ospiti tramite `sertor install rag` e `sertor-flow install` portano un debito di **stile e
leggibilità** accumulato durante lo sviluppo rapido (audit ISSUE-08). Quattro sintomi: **(1)**
*ALL-CAPS enfatico pervasivo* — parole intere in maiuscolo (`MANDATORY`, `ONLY`, `DO NOT`, `ASSISTED`,
`DETERMINISTIC`, …) usate come marcatori d'enfasi in prosa, mentre il rubric di stile del progetto
preferisce **bold** o forma imperativa accompagnata dalla motivazione (*why*); **(2)** *sezioni
ridondanti* — «What NOT to do» e «Hard boundary» che ripetono regole già espresse inline nei passi
procedurali, gonfiando i file e aumentando il rischio di derive silenziose (si modifica un posto, non
l'altro); **(3)** *`wiki-playbook.md` (282 righe) senza Table of Contents*, malgrado 8 sezioni
numerate; **(4)** *un wikilink orfano* `[[assistant-targeting]]` che su un host terzo non risolve (la
pagina vive solo nel wiki dogfood di Sertor, non è distribuita). Il valore: asset più **leggibili e
manutenibili** per l'agente frontier dell'ospite, per il manutentore e per l'auditor — **senza cambiare
il comportamento** delle skill. Nessun sintomo è critico; l'insieme degrada la qualità degli asset
distribuiti.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è la **qualità e
> realtà del contesto reso all'agente**. Le skill distribuite *sono* contesto operativo che l'agente
> frontier dell'ospite legge per agire: una skill piena di ALL-CAPS incongruenti, di regole duplicate e
> di un wikilink che punta a una pagina inesistente sull'ospite è contesto **rumoroso e fuorviante**.
> Ripulirla — preservando ogni istruzione load-bearing — *rafforza* la qualità del contesto reso
> all'agente senza toccare il fronte di valore (il retrieval fuso code+doc). È coerente col confine
> **D↔N**: la pulizia è puramente di **forma/leggibilità** di asset host-facing, **nessun codice del
> core**, **nessun LLM**. Complementa FEAT-021 (che ha già ridotto la duplicazione «How to invoke» nei
> blocchi `CLAUDE.md` e nel body di `guided-setup`): questa feature sistema lo strato sottostante — i
> body delle skill — e lascia a FEAT-024 il freno deterministico (budget altitude in CI) che impedisce
> il re-accumulo.

> **Natura del cambiamento: ADDITIVA / igiene host-facing, ZERO codice di core.** La feature **non**
> modifica `sertor_core` né alcun comando/vehicle/porta/adapter/engine (Principio XI). Tocca
> **esclusivamente asset distribuiti** (file `.md` delle skill) e le loro guardie. La modifica è
> **puramente di forma**: ogni istruzione load-bearing resta presente — cambia solo la sua
> formulazione (ALL-CAPS → imperativo + *why*) o la sua collocazione (regola duplicata condensata in un
> solo posto). **Zero cambiamento di comportamento/semantica** delle skill: un agente che legge il body
> modificato riceve le stesse istruzioni operative di prima, espresse in forma più leggibile.

> **Decisioni di scope — FISSATE con l'utente (erano le forche aperte del §10 dei requirements).**
> **(DA-1)** I callout «How to invoke» inline in `eval-suite-author/SKILL.md` (~31–37) e
> `eval-feedback/SKILL.md` (~31–37) — ridondanti col riferimento unico `sertor-cli-reference.md`
> introdotto da FEAT-021 — sono **in ambito** e vanno **sostituiti con un pointer** allo stesso
> reference, *closure-safe* (stesso pattern host-agnostico di FEAT-021: nessun pointer morto se la
> capacità è installata da sola). Questo completa l'obiettivo «How to invoke in una sola fonte».
> **(DA-2)** La normalizzazione ALL-CAPS si applica **anche** a `requirements/SKILL.md` di
> `sertor-flow` (è una skill distribuita): **solo stile** (maiuscolo enfatico → imperativo + *why*); la
> **lingua resta invariata** (l'eventuale IT→EN è E12, fuori ambito). **(DA-3)** Il wikilink orfano
> `[[assistant-targeting]]` va reso **host-agnostico**: un asset distribuito non deve linkare una
> pagina del wiki interno di Sertor (orfana sull'ospite) → sostituito con prosa semplice senza wikilink,
> o rimosso se non load-bearing. (Il *come* esatto è plan; la direzione è: nessun riferimento al wiki
> interno.)

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Gli asset in scope esistono già e
> sono inventariati (stato su `master`): skill `sertor` —
> `assets/rag/skills/guided-setup/SKILL.md` (190), `assets/rag/skills/eval-suite-author/SKILL.md`
> (146), `assets/rag/skills/eval-feedback/SKILL.md` (77), `assets/claude/skills/wiki-author/SKILL.md`
> (41, già pulito) + `wiki-playbook.md` (282); skill `sertor-flow` —
> `assets/.../skills/requirements/SKILL.md` (164). Il riferimento unico
> `assets/rag/sertor-cli-reference.md` esiste già (FEAT-021). Le copie dogfood sotto `.claude/skills/`
> sono derivate dei canonici, tenute in sync da `tests/unit/test_assets_sync.py`; la parità Copilot è
> presidiata da `packages/sertor/tests/test_assets_copilot_guard.py`. I riferimenti **ancorano** i
> requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Le skill distribuite non gridano più in ALL-CAPS (P2, Should)
L'agente frontier dell'ospite e il manutentore leggono body in prosa pulita: l'enfasi è espressa con
**bold** o forma imperativa + motivazione, non con parole intere in maiuscolo. Gli acronimi tecnici
legittimi (RAG, CLI, MCP, API, JSON, YAML, URL, TOML, NL, POSIX, STOP) e il contenuto in blocchi/span
di codice restano intatti.

**Independent Test**: una grep del pattern ALL-CAPS enfatico (`[A-Z]{4,}` come parola intera,
escludendo acronimi tecnici e righe di codice) sui file in scope restituisce **zero** occorrenze; ogni
sostituzione conserva la motivazione (*why*) nella stessa frase o in quella adiacente.

**Acceptance**:
1. **Given** un body skill in scope con ALL-CAPS enfatico (es. «`--assistant <host>` is MANDATORY»),
   **When** lo si normalizza, **Then** il maiuscolo enfatico è sostituito da bold o forma imperativa
   equivalente che preserva il significato originale.
2. **Given** una sostituzione di ALL-CAPS, **When** la si applica, **Then** la motivazione/regola che il
   maiuscolo accompagnava resta nel body (stessa frase o frase adiacente), non viene rimossa.
3. **Given** un acronimo tecnico legittimo o testo dentro code span/blocco/output CLI citato, **When**
   si applica la normalizzazione, **Then** non viene toccato.

### User Story 2 — Ogni proibizione vive in un solo posto (P2, Should)
Le sezioni «What NOT to do» e «Hard boundary» non ripetono più regole già espresse inline nei passi
procedurali. Ogni proibizione (es. «do not import the core», «do not run without confirmation», «do not
select a provider automatically») compare in **al più una** sezione. Le regole che esistono *solo* in
una delle due sezioni sono conservate.

**Independent Test**: leggendo le sezioni «Hard boundary» e «What NOT to do» (o la sezione unificata
risultante) di ogni file modificato, non si trova alcuna regola identica o semanticamente equivalente in
più di un posto sui casi noti del §1.2 dei requirements; nessuna regola unica viene persa.

**Acceptance**:
1. **Given** una skill con una regola espressa inline (o in «Hard boundary») **e** ripetuta verbatim in
   «What NOT to do», **When** si condensa, **Then** la regola resta in un solo posto.
2. **Given** una proibizione presente **solo** in «What NOT to do» e assente altrove, **When** si
   condensa/fonde, **Then** quella proibizione **non** viene eliminata (conservata).
3. **Given** che la condensazione lasci una «What NOT to do» vuota o con un solo elemento, **When** si
   decide come chiuderla, **Then** la si mantiene come breve promemoria o se ne piega l'unico elemento
   in «Hard boundary»/inline — la scelta che preserva la leggibilità — senza perdere informazione.

### User Story 3 — `wiki-playbook.md` è navigabile via Table of Contents (P1, Must)
Il file di 282 righe con 8 sezioni numerate (§0–§7) ha una Table of Contents in testa al corpo (dopo il
blockquote introduttivo) con link alle sezioni, così chi lo legge — agente o manutentore — naviga senza
scorrere l'intero file.

**Independent Test**: il file `wiki-playbook.md` contiene, come prima sezione del corpo, una lista di
link a tutte le sezioni numerate §0–§7; i link usano anchor Markdown standard navigabili in qualunque
renderer.

**Acceptance**:
1. **Given** `wiki-playbook.md` (282 righe, 8 sezioni numerate), **When** lo si apre, **Then** subito
   dopo il blockquote introduttivo compare una Table of Contents con link a tutte le sezioni §0–§7.
2. **Given** la ToC, **When** la si usa in un renderer Markdown, **Then** i link sono anchor standard e
   portano alle sezioni corrette.
3. **Given** la ToC aggiunta, **When** si verifica il corpo, **Then** nessun titolo o contenuto di
   sezione è alterato (solo aggiunta della ToC, nessuna ristrutturazione).

### User Story 4 — Nessun wikilink orfano raggiunge l'ospite (P1, Must)
Il `wiki-playbook.md` bundlato non contiene più il wikilink `[[assistant-targeting]]` (né altri wikilink
che puntano a pagine non distribuite nel bundle): su un host terzo quel link è orfano e crea confusione
all'agente che legge la skill. La frase che lo conteneva è riscritta in prosa semplice e self-contained,
o rimossa perché il suo contenuto è già coperto dal capoverso circostante.

**Independent Test**: una grep di `[[` negli asset skill distribuiti non produce match (oppure, se
restano wikilink, ogni pagina target è un file presente nell'asset bundle); la frase risultante è
self-contained e non introduce riferimenti a pagine assenti dal bundle dell'ospite.

**Acceptance**:
1. **Given** `wiki-playbook.md` bundlato con `[[assistant-targeting]]`, **When** si applica il fix,
   **Then** il wikilink non è più presente.
2. **Given** la frase che lo conteneva, **When** la si riscrive (o rimuove), **Then** il risultato è
   prosa semplice, self-contained, senza riferimenti a pagine non incluse nel bundle distribuito.
3. **Given** gli asset skill distribuiti, **When** se ne verifica il contenuto, **Then** non restano
   wikilink orfani (verso pagine non distribuite).

### User Story 5 — «How to invoke» vive in una sola fonte (P3, Could)
I callout «How to invoke» inline in `eval-suite-author/SKILL.md` e `eval-feedback/SKILL.md`, ridondanti
col riferimento unico `sertor-cli-reference.md` (FEAT-021), sono sostituiti da un **pointer** allo
stesso reference — coerentemente con quanto FEAT-021 ha già fatto per `guided-setup`. Il pointer è
*closure-safe*: se la capacità è installata da sola, non resta un puntatore morto.

**Independent Test**: i body di `eval-suite-author/SKILL.md` e `eval-feedback/SKILL.md` non contengono
più il callout «How to invoke» espanso ma un pointer a `sertor-cli-reference.md`; il reference target è
presente nel bundle quando la skill è distribuita (closure verificata offline, stesso pattern FEAT-021).

**Acceptance**:
1. **Given** i due body eval-skills con «How to invoke» inline, **When** si applica la condensazione,
   **Then** ciascuno punta al riferimento unico `sertor-cli-reference.md` invece di ripetere le
   istruzioni di invocazione.
2. **Given** il pointer aggiunto, **When** la skill è distribuita, **Then** il target del pointer è
   presente nel bundle (nessun pointer morto), coerente con la chiusura asset di FEAT-021.
3. **Given** lo scope FEAT-021, **When** si applica questa condensazione, **Then** non si re-introduce
   né si espande «How to invoke» in alcun altro body.

### User Story 6 — La pulizia non cambia il comportamento delle skill (P1, Must)
Le azioni da eseguire, l'ordine dei passi, le regole di consenso e le restrizioni sui vehicle restano
identici: cambia solo la forma. Un confronto leggibile prima/dopo non rivela diff semantici.

**Independent Test**: per ogni file modificato, un confronto del contenuto standing (regole, passi,
restrizioni) prima/dopo non rivela alcun cambiamento semantico; la guardia di parità Copilot resta
verde; nessuna istruzione load-bearing è scomparsa.

**Acceptance**:
1. **Given** una skill prima/dopo la pulizia, **When** se ne confrontano le istruzioni operative,
   **Then** sono le stesse (stesse azioni, stesso ordine, stesse restrizioni), solo riformulate.
2. **Given** una regola load-bearing presente nell'originale, **When** si applica la pulizia, **Then**
   resta presente nel body (eventualmente in collocazione diversa), mai persa.
3. **Given** la distinzione «ripetizione di regola già inline» vs «regola che esiste solo lì», **When**
   si condensa, **Then** solo le ripetizioni sono rimosse; le regole uniche sono conservate.

### User Story 7 — La parità host-agnostica Claude↔Copilot è preservata (P1, Must)
I body modificati restano host-agnostici: niente path `.claude/`, niente slash-command, niente
nome-modello/prodotto Claude-only. Stessa leggibilità su Claude e Copilot CLI; le guardie di parità
restano verdi.

**Independent Test**: i body modificati non introducono path `.claude/`, slash-command o
nomi-modello/prodotto Claude-only; la guardia di parità Copilot
(`test_assets_copilot_guard.py`) resta verde.

**Acceptance**:
1. **Given** un body skill modificato, **When** lo si ispeziona, **Then** non contiene path `.claude/`,
   slash-command, né nome-modello/prodotto Claude-only.
2. **Given** la guardia di parità Copilot esistente, **When** gira dopo la feature, **Then** resta
   verde.
3. **Given** le due famiglie di distribuzione, **When** si confrontano gli asset risultanti, **Then** la
   leggibilità e l'host-agnosticità sono preservate.

### User Story 8 — Le copie dogfood restano in sync (P2, Should)
Le copie dogfood sotto `.claude/skills/` sono ri-sincronizzate con gli asset canonici dopo le modifiche,
così restano byte-identiche, verificato dalla guardia di sync esistente.

**Independent Test**: dopo aver modificato gli asset canonici, le copie `.claude/` sono ri-sincronizzate
(`python -m sertor_installer.sync`) e la guardia `tests/unit/test_assets_sync.py` resta verde.

**Acceptance**:
1. **Given** gli asset canonici modificati (`wiki-playbook.md`, `requirements/SKILL.md` e ogni altro
   coperto dal sync), **When** si esegue il sync, **Then** le copie dogfood `.claude/` sono byte-identiche
   e la guardia di sync è verde.
2. **Given** il lifecycle install/upgrade/uninstall delle capacità `rag` e `governance`, **When** lo si
   esegue, **Then** resta coerente: i file skill continuano a essere depositati/rimossi come prima
   (additività, nessuna capacità rimossa).

### User Story 9 — Una guardia anti-regressione protegge gli invarianti (P2, Should/Could)
Un test di guardia fallisce se un file in scope reintroduce ALL-CAPS enfatico sui casi noti, un wikilink
orfano nel bundle, un «How to invoke» espanso in più di una fonte, o se cambia il contenuto standing
(semantica) di una skill. Così gli invarianti sono protetti in CI, non solo introdotti una volta.

**Independent Test**: reintroducendo un ALL-CAPS enfatico su un caso noto, un wikilink orfano nel
bundle, o un «How to invoke» espanso, almeno un test di guardia fallisce; allo stato corretto la guardia
passa.

**Acceptance**:
1. **Given** un file skill in scope, **When** reintroduce un ALL-CAPS enfatico su un caso noto, **Then**
   la guardia fallisce (grep ALL-CAPS = 0 violata).
2. **Given** il bundle distribuito, **When** un wikilink orfano è reintrodotto, **Then** la guardia
   fallisce (zero wikilink orfani violato).
3. **Given** lo scope FEAT-021, **When** un «How to invoke» espanso compare in più di una fonte, **Then**
   la guardia (estensione di quella FEAT-021) fallisce.
4. **Given** lo stato corretto, **When** la guardia gira, **Then** passa.

## Edge Cases
- **ALL-CAPS legittimo** (acronimo tecnico RAG/CLI/MCP/…, keyword letterale `STOP`, contenuto in code
  span/blocco/output CLI citato): **non** toccato (US1, FR-003).
- **ALL-CAPS che accompagna una regola**: la sostituzione conserva la motivazione/regola; rimuovere il
  maiuscolo non rimuove il *why* (US1, FR-002).
- **Regola presente solo in «What NOT to do»**: conservata, mai eliminata nella condensazione (US2,
  FR-005).
- **«What NOT to do» ridotta a vuota/single-item**: mantenuta come breve promemoria o piegata in «Hard
  boundary»/inline, secondo leggibilità (US2, FR-006).
- **Wikilink rimosso ma frase lasciata monca**: la frase è riscritta self-contained o rimossa intera,
  mai lasciata con un riferimento vuoto (US4, FR-008/009).
- **Wikilink diverso da `[[assistant-targeting]]` verso pagina non distribuita**: stesso trattamento —
  nessun wikilink orfano resta nel bundle (US4, FR-008).
- **Pointer «How to invoke» morto**: closure-safe — il target `sertor-cli-reference.md` è presente
  quando la skill è distribuita; nessun pointer morto (US5, FR-010, coerente FEAT-021).
- **`requirements/SKILL.md` in italiano**: solo lo stile ALL-CAPS è normalizzato (es. «SEMPRE» →
  «sempre»); la lingua resta invariata (IT→EN è E12, fuori ambito) (DA-2, FR-001).
- **Drift dogfood↔bundle**: la guardia di sync impedisce divergenze tra `.claude/` e i canonici (US8,
  FR-013).
- **Reintroduzione di ALL-CAPS / wikilink orfano / «How to invoke» espanso / cambiamento semantico**: la
  guardia anti-regressione fallisce (US9, FR-014).

## Requirements *(mandatory)*

### Requisiti funzionali

**Riduzione ALL-CAPS enfatico**
- **FR-001 (normalizzazione ALL-CAPS).** Nei body in prosa degli asset skill in scope (inclusa
  `requirements/SKILL.md` di `sertor-flow`, solo stile, lingua invariata), ogni parola intera in
  maiuscolo usata come enfasi è sostituita con una formulazione bold o imperativa equivalente che
  preserva il significato originale. *(REQ-001; DA-2; CS-1)*
- **FR-002 (preserva il *why*).** Sostituendo un marcatore ALL-CAPS, la motivazione/regola che
  accompagnava non viene rimossa: il *why* resta nel body (stessa frase o frase adiacente). *(REQ-002;
  CS-2)*
- **FR-003 (escludi acronimi e codice).** Non vengono alterati gli ALL-CAPS che sono acronimi legittimi
  (RAG, CLI, MCP, API, JSON, YAML, URL, TOML, NL, POSIX, STOP) o che compaiono in code span, blocchi di
  codice o output CLI citato. *(REQ-003; CS-1)*

**Condensazione sezioni ridondanti**
- **FR-004 (una proibizione, un posto).** Ogni regola proibitiva compare in al più una sezione per file:
  se è espressa inline nei passi o in «Hard boundary», non è ripetuta verbatim in «What NOT to do».
  *(REQ-004; CS-2)*
- **FR-005 (conserva le regole uniche).** Condensando/fondendo sezioni sovrapposte, ogni proibizione
  presente in *una sola* delle due sezioni (e assente altrove) è conservata, mai eliminata. *(REQ-005;
  CS-2)*
- **FR-006 (chiusura della sezione svuotata).** Se la fusione lascia una «What NOT to do» vuota o con un
  solo elemento, la sezione è mantenuta come breve promemoria o il suo unico elemento è piegato in «Hard
  boundary»/inline — la scelta che preserva la leggibilità. *(REQ-006; CS-2)*

**Table of Contents per `wiki-playbook.md`**
- **FR-007 (ToC navigabile).** L'asset `wiki-playbook.md` contiene, subito dopo il blockquote
  introduttivo, una Table of Contents con link a tutte le sezioni numerate §0–§7, usando anchor Markdown
  standard navigabili in qualunque renderer; nessun titolo o contenuto di sezione è alterato. *(REQ-007;
  CS-3)*

**Wikilink orfano**
- **FR-008 (rimozione wikilink orfano).** Il `wiki-playbook.md` bundlato non contiene il wikilink
  `[[assistant-targeting]]` né altri wikilink verso pagine non incluse nel bundle distribuito; la frase
  che lo conteneva è riscritta in prosa semplice o rimossa se già coperta dal capoverso. *(REQ-008;
  DA-3; CS-4)*
- **FR-009 (riscrittura self-contained).** Se si sceglie la riscrittura, la frase risultante è
  self-contained e non introduce riferimenti a pagine assenti dal bundle dell'ospite. *(REQ-009;
  DA-3; CS-4)*

**«How to invoke» in una sola fonte (DA-1)**
- **FR-010 (pointer al reference unico).** I callout «How to invoke» inline in `eval-suite-author/SKILL.md`
  e `eval-feedback/SKILL.md` sono sostituiti da un pointer a `sertor-cli-reference.md` (coerente con la
  chiusura di FEAT-021 per `guided-setup`); il pointer è closure-safe (nessun pointer morto se la
  capacità è installata da sola). *(REQ-Could §9 requirements; DA-1; CS-2)*

**Parità, sync, anti-regressione, lifecycle**
- **FR-011 (host-agnostico).** I body modificati restano host-agnostici: niente path `.claude/`, niente
  slash-command, niente nome-modello/prodotto Claude-only; la guardia di parità Copilot resta verde.
  *(REQ-011; NFR-2; CS-5)*
- **FR-012 (nessun cambiamento semantico).** La semantica comportamentale delle skill (azioni, ordine
  dei passi, regole di consenso, restrizioni sui vehicle) non cambia; ogni istruzione load-bearing resta
  presente. *(REQ-005/NFR-3; CS-5)*
- **FR-013 (sync dogfood↔bundle).** Modificati gli asset canonici, le copie dogfood sotto `.claude/` sono
  ri-sincronizzate così le due restano byte-identiche; la guardia di sync esistente resta verde.
  *(REQ-010; CS-6)*
- **FR-014 (guardia anti-regressione).** La feature fornisce una guardia che fallisce se un file in scope
  reintroduce ALL-CAPS enfatico su un caso noto, un wikilink orfano nel bundle, un «How to invoke»
  espanso in più di una fonte (estensione della guardia FEAT-021), o un cambiamento del contenuto
  standing (pin della semantica). *(REQ-Could §9; CS-1/CS-2/CS-4/CS-5)*
- **FR-015 (lifecycle additivo).** Il cambiamento è additivo all'installer: nessuna capacità rimossa; il
  lifecycle install/upgrade/uninstall delle capacità `rag` e `governance` resta coerente; i file skill
  continuano a essere depositati/rimossi come prima. *(REQ-012)*

### Requisiti non funzionali
- **RNF-1 (Principio XI):** zero modifiche a `sertor_core` — la feature tocca esclusivamente asset
  host-facing (file `.md`), nessun engine/porta/adapter/comando/servizio del core. *(NFR-1; NFR-6)*
- **RNF-2 (Principio X — host-agnostico):** i body modificati restano host-agnostici, byte-identici tra
  Claude e Copilot CLI; nessun path letterale dell'assistente, slash-command o nome-modello Claude.
  *(NFR-2)*
- **RNF-3 (non-regressione semantica):** la semantica comportamentale non cambia; un agente che legge il
  body modificato riceve le stesse istruzioni operative, in forma più leggibile. *(NFR-3)*
- **RNF-4 (non-regressione suite):** le suite esistenti (`sertor`, `sertor-install-kit`, `sertor-flow`,
  root) restano verdi — in particolare `test_assets_copilot_guard.py` e `test_assets_sync.py`. *(NFR-4)*
- **RNF-5 (coerenza con FEAT-021):** la pulizia non re-introduce né espande «How to invoke» in alcun
  body; dove FEAT-021 ha già sostituito con un pointer, quel pointer resta tale. *(NFR-5)*

### Key Entities
- **Asset skill in scope** — i file `.md` di skill distribuiti, inventariati: `guided-setup/SKILL.md`,
  `eval-suite-author/SKILL.md`, `eval-feedback/SKILL.md`, `wiki-author/wiki-playbook.md` (pacchetto
  `sertor`); `requirements/SKILL.md` (pacchetto `sertor-flow`). `wiki-author/SKILL.md` (41 righe, già
  pulito) non richiede intervento.
- **Riferimento unico CLI** — `sertor-cli-reference.md` (introdotto da FEAT-021, non modificato qui):
  destinazione del pointer «How to invoke» per le eval-skills (DA-1), closure-safe.
- **Table of Contents** — la lista di anchor link alle sezioni §0–§7 in testa al corpo di
  `wiki-playbook.md` (forma = *come* di plan).
- **Wikilink orfano** — `[[assistant-targeting]]` (riga ~52 di `wiki-playbook.md`): riferimento al wiki
  interno di Sertor, orfano sull'ospite; rimosso/riscritto in prosa host-agnostica.
- **Copie dogfood** — le copie sotto `.claude/skills/` derivate dai canonici, ri-sincronizzate e
  byte-identiche, presidiate da `test_assets_sync.py`.
- **Guardia anti-regressione** — il test che fallisce su reintroduzione di ALL-CAPS noto / wikilink
  orfano / «How to invoke» espanso / cambiamento semantico; affiancata dalle guardie esistenti
  (parità Copilot, sync dogfood↔bundle).

## Success Criteria *(mandatory)*
- **CS-1 (ALL-CAPS eliminato):** nei body in prosa degli asset skill in scope, il numero di parole
  intere in maiuscolo usate come enfasi (escludendo acronimi tecnici e blocchi di codice) è **zero** —
  verificabile con una grep `[A-Z]{4,}` sui file modificati, escludendo le righe di solo codice. *(FR-001/002/003,
  US1)*
- **CS-2 (sezioni ridondanti rimosse o condensate):** ogni file skill modificato non contiene regole
  identiche o semanticamente equivalenti in più di una sezione; ogni proibizione compare in un solo
  posto e nessuna regola unica è persa — verificabile sui casi noti del §1.2 dei requirements. *(FR-004/005/006/010,
  US2/US5)*
- **CS-3 (ToC presente in `wiki-playbook.md`):** il file contiene una Table of Contents come prima
  sezione del corpo (dopo il blockquote iniziale) con link alle sezioni §0–§7 — verificabile
  meccanicamente (≥8 titoli `## ` + lista `- [§N …](#…)` in testa). *(FR-007, US3)*
- **CS-4 (zero wikilink orfani negli asset distribuiti):** il `wiki-playbook.md` bundlato non contiene
  `[[assistant-targeting]]` né altri wikilink verso pagine non distribuite — verificabile con grep `[[`
  che non produce match orfani. *(FR-008/009, US4)*
- **CS-5 (nessun cambiamento semantico):** il comportamento atteso delle skill (azioni, ordine dei
  passi, regole di consenso, restrizioni sui vehicle) non cambia; la guardia di parità Copilot resta
  verde; un confronto leggibile prima/dopo non rivela diff semantici. *(FR-011/012/014, US6/US7)*
- **CS-6 (sync dogfood preservato):** le copie dogfood in `.claude/skills/` restano in byte-parità con
  gli asset bundlati dopo `python -m sertor_installer.sync`; la guardia di sync è verde. *(FR-013/015,
  US8)*

## Assumptions
- **A-001 — Nessuna perdita load-bearing:** ogni regola rimossa da una sezione per ridondanza è
  effettivamente già presente altrove nello stesso file; il plan verifica file per file la conservazione
  prima di eliminare. *(FR-004/005)*
- **A-002 — Wikilink = non load-bearing:** la frase che contiene `[[assistant-targeting]]` è informativa
  e non porta alcuna istruzione che influenzi il comportamento dell'agente; rimozione o riscrittura in
  prosa semplice è sicura. *(FR-008/009)*
- **A-003 — FEAT-021 completata:** `sertor-cli-reference.md` esiste già nel bundle; il pointer «How to
  invoke» delle eval-skills può puntarvi (closure-safe, stesso pattern FEAT-021). *(FR-010)*
- **A-004 — Guardie esistenti riusate/estese:** `test_assets_sync.py` e `test_assets_copilot_guard.py`
  esistono; la feature le riusa/estende, non le reinventa; restano verdi dopo il ri-sync. *(FR-013/014)*
- **A-005 — `requirements/SKILL.md` resta in italiano:** la normalizzazione è solo di stile (maiuscolo
  enfatico → imperativo); la lingua non cambia (IT→EN è E12). *(DA-2, FR-001)*

### Fuori ambito (dichiarato)
- **Modifiche a `sertor_core`** o a qualunque comando/vehicle — la feature è additiva e host-facing,
  zero codice di runtime del core (Principio XI).
- **Agenti distribuiti** (`concierge.md`, `wiki-curator.md`, `configuration-manager.md`,
  `requirements-analyst.md`): questa feature è scoped sulle **skill**; gli agenti hanno stili diversi e
  sono oggetto di interventi autonomi se necessario.
- **Blocchi `CLAUDE.md`** (`claude-md-block*.md`): già sistemati da FEAT-021.
- **`sertor-cli-reference.md`**: introdotto da FEAT-021, non toccato qui (solo destinazione del pointer).
- **`wiki-author/SKILL.md`** (41 righe): già pulito, nessun intervento.
- **Traduzione di lingua** (IT→EN di `requirements/SKILL.md`): **E12**, fuori ambito.
- **Budget altitude in CI** (gate che fallisce se un file skill supera N righe): **FEAT-024** — questa
  feature riduce il debito; FEAT-024 mette il freno deterministico contro il re-accumulo.
- **Stub `assets/copilot/`** (onestà sui surface Copilot inerti): **FEAT-023**.
- **Il *come* di dettaglio** (criterio operativo ALL-CAPS-vs-enfasi-legittima; forma esatta della ToC e
  delle anchor; forma esatta della riscrittura del wikilink; forma della guardia anti-regressione): fase
  di **design/plan**.

> **Tracciamento dello scope.** I rinvii reali sono già **promossi a casa durevole** nel backlog
> d'epica: budget altitude in CI → **FEAT-024**; stub/onestà surface Copilot → **FEAT-023**; traduzione
> lingua → **E12**; pulizia agenti distribuiti → intervento autonomo separato. Nessun rinvio reale resta
> sepolto in `specs/`. La feature è *done* quando: ALL-CAPS enfatico = 0 sui file in scope; nessuna
> regola duplicata inline↔sezione; ToC presente in `wiki-playbook.md`; zero wikilink orfani nel bundle;
> «How to invoke» in una sola fonte; copie dogfood in sync; guardie (anti-regressione + parità +
> sync) verdi; asset distribuiti via installer (additivi).

### Forche di design — per `/speckit-plan` (sono *come*, non scope)
- **DA-D-1 — Criterio operativo «ALL-CAPS → imperativo + why»:** quando un maiuscolo è enfasi legittima
  (da preservare) vs enfasi da convertire — regola precisa e lista di esclusione (acronimi/code/output
  CLI). *(come di plan)*
- **DA-D-2 — Forma della ToC del `wiki-playbook.md`:** solo le sezioni principali §0–§7 (più stabile) o
  anche le sottosezioni (più granulare ma da mantenere); forma esatta delle anchor. CS-3 richiede almeno
  §0–§7. *(come di plan)*
- **DA-D-3 — Forma esatta della sostituzione del wikilink orfano:** riscrittura in prosa vs rimozione
  della frase; testo risultante self-contained. *(come di plan; direzione DA-3 fissata: niente
  riferimento al wiki interno)*
- **DA-D-4 — Forma della guardia anti-regressione:** grep ALL-CAPS = 0 sui casi noti + zero `[[wikilink]]`
  orfani nel bundle + «How to invoke» in una sola fonte (estensione guardia FEAT-021) + pin del
  contenuto standing (nessun cambiamento semantico); confine di esclusione preciso per la grep
  ALL-CAPS. *(come di plan)*
- **DA-D-5 — Regola di condensazione «Hard boundary» + «What NOT to do»:** (A) tenere entrambe rimuovendo
  solo i duplicati, (B) fondere in una sola «Boundaries», (C) tenere «Hard boundary» per le restrizioni
  architetturali e «What NOT to do» per le specifiche di flusso non espresse nei passi. Il *cosa*
  (nessuna duplicazione) è FR-004; la struttura risultante è plan. *(come di plan)*
