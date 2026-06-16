# Epica — Second brain cross-progetto (il «Sertor dei Sertor» / Meta-Sertor)
<!-- STATO: APERTA, idea-visione DA ESPANDERE. Bivi aperti (§9) da sciogliere PRIMA di decomporre.
     Pagina-visione di riferimento: wiki/syntheses/second-brain-cross-progetto.md -->

> **Epica trasversale e ricorsiva.** Aggiunge un'**altitudine sopra i singoli Sertor**: una conoscenza
> condivisa, di più alto livello e meno dettagliata, di **tutti** i propri progetti — e un **registry di
> asset** (skill/agent/hook/template) che la flotta produce e consuma. È **Sertor applicato a se stesso,
> un piano più su** (L2). Tocca core, wiki, installer e l'epica `multiutente` insieme. Tesi, diagrammi e
> rischi in dettaglio: [[second-brain-cross-progetto]]. Si decompone in
> `requirements/second-brain/<feature>/requirements.md` (EARS) **quando i bivi §9 sono decisi**.

## 1. Visione e problema (perché)

Con il lavoro agentico, una persona/piccolo team lavora su **molti progetti in parallelo**. Ogni progetto
accumula con Sertor la propria conoscenza (wiki) e i propri **asset** (skill, agent, hook, playbook). Ma
restano **prigionieri del singolo contesto**: una lesson imparata su un progetto non aiuta gli altri; una
skill nata in un repo va riscritta a mano per riusarla; non esiste un luogo dove le esperienze di N
progetti si **fondano** in qualcosa di più alto.

Serve un **terzo strato di altitudine** sopra il diario e il grafo del wiki ([[diary-vs-graph]]):

- **L0** = artefatti grezzi (codice, spec) — grounded, dettagliatissimi.
- **L1** = wiki di progetto (conoscenza distillata di *un* contesto) — **esiste già**.
- **L2** = Meta-Sertor (conoscenza distillata **trasversale** + registry asset + catalogo flotta) — **il nuovo**.

Tecnicamente **L2 è un'istanza di `sertor-core`** il cui corpus è l'output distillato dei Sertor di
progetto: il motore esiste; il nuovo è il **confine di promozione** (giudizio) tra L1 e L2 e, per gli
asset, la **verifica + parametrizzazione**. Sertor passa da **autore** a **giardiniere di una flotta
auto-migliorante**.

> Il *come* (motore L2, pipeline, meta-grafo) è materia della **fase di design**. Qui solo *cosa* e *perché*.

## 2. Ambito

### In ambito (dell'epica, da decomporre poi)
- **Catalogo / meta-roadmap** della flotta: vista trasversale «dove siamo su tutti i progetti», assemblata
  dai blocchi `EXEC` di ogni roadmap.
- **Query federata cross-progetto con escalation**: prima L2 (astratto), poi fan-out sui corpora dei
  progetti (riusa la feature 010).
- **Harvest & promote**: la distillazione cross-progetto — raccolta candidati (meccanico) + promozione a
  meta-conoscenza de-contestualizzata (giudizio), con provenance verso L1.
- **Seed & apply**: bootstrap di un progetto nuovo dalla saggezza accumulata.
- **Asset registry**: catalogo versionato di skill/agent/hook/template con provenance, «dove è usato»,
  propagazione update; l'installer come canale di distribuzione (direzione invertita: host→registry→host).
- **Trust al meta-livello**: confidence, **corroborazione** (quanti progetti confermano), decay, validità
  temporale, supersession.
- **Verifica & sicurezza degli asset**: il test che **viaggia con l'asset** + gate supply-chain prima che
  un asset attraversi il confine di un progetto.

### Fuori ambito
- **Modello push** (ogni progetto pubblica verso un servizio): si adotta il **pull** (L2 legge i wiki come
  corpus; accoppiamento lasco, Principio X).
- **Collaborazione multiutente** in sé (ownership, sync, conflict-resolution): è l'epica
  [`../multiutente/epic.md`](../multiutente/epic.md) — L2 ne sarà semmai il **primo caso d'uso concreto**.
- **Roll-up di telemetria** di flotta: confine con `osservabilita` (lì confermato fuori scope, store
  per-progetto).
- Definizione del *come* (motore L2, meta-grafo, registry): fase di **design**.

## 3. Criteri di successo
- **CS-1 (catalogo):** da un registro di progetti (config con path/remote), il sistema produce una vista
  trasversale dello stato (in progress/bloccato/shippato) **senza** che i progetti sappiano che L2 esiste.
- **CS-2 (query federata):** una domanda «l'ho già risolto, da qualche parte?» interroga L2 e, se serve,
  escala in fan-out sui corpora dei progetti, restituendo risultati con **provenance**.
- **CS-3 (promozione grounded):** ogni meta-claim promosso conserva i **link a L1** da cui è stato
  distillato; applicarlo a un progetto nuovo comporta un **ri-ancoraggio** alla realtà attuale del target.
- **CS-4 (asset portabile e verificato):** un asset promosso viaggia con il proprio **contratto/smoke
  test**, è **parametrizzato** (intento ↔ binding), e viene **adottato solo se il test passa** nel target.
- **CS-5 (sicurezza):** in **0** casi un asset attivo (hook/script) attraversa il confine di un progetto
  senza un gate esplicito di review/approvazione.
- **CS-6 (accoppiamento lasco):** L2 resta **opzionale/osservatore**; nessun progetto diventa dipendente
  hard da L2 (Principio X portato all'altitudine di flotta).

## 4. Stakeholder e attori
- **Owner/maintainer della flotta (tu):** il giardiniere — promuove, distribuisce, cura la conoscenza trasversale.
- **I singoli progetti (L1):** **produttori** (sorgente di harvest) **e** consumatori (seed/apply, asset).
- **Agente LLM:** consumatore della query federata; esecutore degli asset distribuiti.
- **Epica `multiutente`:** se la flotta è di team, L2 ne attiva privacy/ownership/sicurezza.
- **L'installer ([[sertor-installer]]):** canale di distribuzione degli asset dal registry.

## 5. Vincoli, assunzioni e dipendenze
- **Riuso massimo:** motore L2 = istanza `sertor-core`; query federata = feature 010; provenance/
  supersession = modello `status: superseded` del wiki (feature 017); de-contestualizzazione = la
  metodologia con cui Sertor si è reso host-agnostico (**Principio X**).
- **Pull, non push:** L2 legge; i progetti non pubblicano. Il «registro progetti» è una config con path/remote.
- **Promozione lossy e selettiva:** si promuove poco e bene; soglia di **corroborazione** o stato
  `provisional` contro l'astrazione prematura.
- **Provenance obbligatoria:** la meta-conoscenza non è mai autoritativa da sola — propone, il progetto dispone.
- **Asset = codice attivo:** verifica + gate di sicurezza non sono opzionali.
- **Dipendenza dai bivi §9:** non si decompone finché i fork (solo/team, meta-corpus vs fan-out, meta-grafo) non sono decisi.

## 6. Rischi
- **R-1 — Tensione con l'ESSENZA (grounding):** un second brain astrae → si allontana dalla ground truth,
  proprio ciò che Sertor difende. **Antidoto:** provenance + ri-ancoraggio + validità temporale.
- **R-2 — Magnete di spazzatura:** promuovere tutto → segnale basso. Promozione **selettiva e lossy**.
- **R-3 — Astrazione prematura (N=1):** generalizzare da un solo caso. Serve soglia di corroborazione/`provisional`.
- **R-4 — Oracolo stantio:** meta-conoscenza creduta perché «di alto livello» mentre contraddice la realtà
  attuale — più pericolosa qui che in L1.
- **R-5 — Asset rotto in flotta:** senza il test-che-viaggia-con-l'asset, si distribuiscono skill spaccate.
- **R-6 — Supply-chain:** eseguire asset altrui senza gate di review/sicurezza.
- **R-7 — Coupling creep:** L2 che diventa dipendenza hard di ogni progetto.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Ubiquitous):** *The meta layer (L2) shall read project wikis as a corpus (pull) without
  requiring the projects to know it exists (loose coupling, Principio X).*
- **REQ-E2 (Ubiquitous):** *Every promoted meta-claim shall carry provenance links back to the grounded L1
  pages it was distilled from, and shall never be authoritative on its own.*
- **REQ-E3 (Unwanted):** *If an active asset (hook/script) would cross a project boundary, then the system
  shall require an explicit review/approval gate before adoption.*
- **REQ-E4 (Optional):** *Where an asset is promoted, it shall travel with its own contract/smoke test and
  be adopted in a target only if that test passes there.*
- **REQ-E5 (State-driven):** *While L2 is unavailable or disabled, the individual projects shall continue
  to operate unchanged (L2 is optional/observer).*

## 8. Backlog di feature (da decomporre dopo i bivi §9)

> Ordinato per **valore/sforzo** (dalla tabella della pagina-visione). MVP proposto = **FEAT-001 + FEAT-002**
> (vedo tutti i miei progetti + chiedo a tutti i miei progetti), quasi solo wiring di primitive esistenti,
> **senza** ancora il giudizio di promozione: valida il valore prima di costruire `promote`.

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Catalogo / meta-roadmap di flotta** — vista trasversale auto-assemblata dai blocchi `EXEC` dei progetti | «Dove siamo su tutti i progetti» a colpo d'occhio | **Must** | da decomporre (1° deliverable, sforzo bassissimo) |
| FEAT-002 | **Query federata cross-progetto + escalation** — interroga L2, poi fan-out sui corpora (riusa feature 010) | «L'ho già risolto, da qualche parte?» | **Should** | da decomporre (basso, quasi wiring) |
| FEAT-003 | **Harvest & promote** — distillazione cross-progetto (raccolta meccanica + promozione a giudizio, de-contestualizzata, con provenance) | Il second brain vero | **Should** | da decomporre (giudizio, medio-alto) |
| FEAT-004 | **Trust al meta-livello** — confidence, corroborazione, decay, validità temporale, supersession | Difesa contro oracolo stantio/astrazione prematura | **Should** | da decomporre |
| FEAT-005 | **Seed & apply** — bootstrap di un progetto nuovo dalla saggezza accumulata | La flotta accelera i progetti nuovi | **Could** | da decomporre |
| FEAT-006 | **Asset registry** — catalogo versionato di skill/agent/hook con provenance, «dove è usato», propagazione update; installer come canale | Riuso degli asset many-to-many | **Could** | da decomporre |
| FEAT-007 | **Verifica & sicurezza degli asset** — test che viaggia con l'asset + parametrizzazione (intento↔binding) + gate supply-chain | Niente skill rotte/insicure in flotta | **Could** | da decomporre |
| FEAT-008 | **Cross-project lint / drift** — lint semantico a livello di flotta (una lesson regge ancora? chi diverge da una metodologia?) | Anti-deriva di flotta | **Could** | da decomporre |
| FEAT-009 | **Codifica di metodologie / sintesi N→1** — pattern ricorrente su N progetti → asset nuovo (clustering varianti + sintesi human-in-the-loop) | Chiude il cerchio conoscenza↔asset | **Could** | da decomporre |
| FEAT-010 | **Meta-grafo dei concetti/asset** — relazioni tipate (`generalizes`/`refines`/`contradicts`/`applies-when`); porta sorella, non il code-graph | Lineage e divergenze tra asset | **Could** | da decomporre — **prima per gli asset** che per la conoscenza |

## 9. Bivi aperti (da decidere PRIMA di decomporre)
- **DA-SB-a — Solo io o piccolo team?** Determina metà delle scelte a valle (privacy, ownership, sync,
  gate sicurezza). Se team → L2 è il primo caso d'uso dell'epica `multiutente`.
- **DA-SB-b — Meta-corpus dedicato (L2 distillato) vs solo fan-out federato?** Probabilmente entrambi con
  escalation; primo taglio possibile = solo fan-out (zero promozione) per validare il valore.
- **DA-SB-c — Meta-grafo in v1?** No per la conoscenza (prosa + ibrido); prima per gli asset (`applies-when`).
- **DA-SB-d — Nome** (Micelio/Cortex/Atlas/Sertorium…): scelta dell'utente.

## 10. Riferimenti
Pagina-visione completa con diagrammi, prior art (PKM/Zettelkasten · memoria agenti MemGPT/Mem0/Zep ·
developer-portal Backstage/Sourcegraph) e analisi rischi: [[second-brain-cross-progetto]]. Correlati:
[[diary-vs-graph]] · [[deterministic-vs-judgment]] · [[sertor-installer]] ·
[[spec-010-query-congiunta-e-upsert-index]] · [[constitution]] (Principio X) · `multiutente/epic.md`.
