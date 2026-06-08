# Wiki-craft — cosa merita una pagina e come si tiene insieme l'insieme

> **Pagina di riferimento (foglia).** Se [`page-craft.md`](page-craft.md) descrive *com'è fatta **una**
> pagina*, **wiki-craft** descrive il livello sopra: *cosa merita di essere una pagina* e *come l'insieme
> tiene insieme* — archetipi di pagina, pagine di struttura, i due assi di navigazione, igiene a livello
> grafo. È **linkata da** chi decide se creare/spostare pagine o giudica la salute del grafo (playbook §3,
> `ops/record.md`, `ops/ingest.md`, `ops/reorg.md`, `ops/lint.md` livello C). È una **foglia**: non dipende
> dal playbook (le operazioni la referenziano, non viceversa).
>
> **Host-agnostica (Principio X).** I principi valgono su qualunque host; ciò che *varia* — le **aree** della
> tassonomia, l'esistenza di tag/categorie, di hub per-area o di una home — viene dal profilo
> (`wiki.config.toml`). La mappatura agli archetipi e gli esempi qui sotto sono il **profilo Sertor**.

## 1. Quando creare una pagina (la regola fondamentale)

Una cosa diventa pagina quando ha **identità propria** ed è **referenziata da più punti**. Due test:

- **Test del link** — se più pagine hanno bisogno di linkare quel concetto, è un'**entità autonoma** →
  pagina propria. Se lo cita **una sola** pagina, è un **paragrafo** dentro quella.
- **Test del nome** — se la cosa ha un **nome stabile** con cui ci si riferisce ad essa («il servizio di
  Billing», «la procedura di onboarding»), probabilmente è una pagina.

**Errore opposto da evitare: frammentazione.** Tante micro-pagine da due righe sono peggio di una pagina
ben strutturata. Crea una pagina quando il contenuto **si regge** ed è **abbastanza referenziato** da
servire altrove. (Il *come* scriverla, una volta decisa: [`page-craft.md`](page-craft.md).)

## 2. Gli archetipi di pagina (che forma dare)

Una wiki sana è fatta di pochi **archetipi** ricorrenti. Riconoscerli dice subito che forma dare a ciò che
stai scrivendo — ed è la distinzione del framework **Diátaxis**: tenere separati questi tipi impedisce alle
pagine di diventare minestroni illeggibili. **Non mescolare** un how-to con una spiegazione filosofica:
*linkali*.

| Archetipo | Cos'è | Esempio |
|---|---|---|
| **Entità / Concetto** | descrive una cosa che esiste: un componente, un termine, un servizio | «Servizio Pagamenti», «idempotenza» |
| **Procedura / How-to** | come si fa qualcosa, passo-passo | «Come fare il deploy in produzione» |
| **Riferimento** | dati consultabili, non narrativi | «Tabella degli endpoint API», «Variabili d'ambiente» |
| **Spiegazione / Discussione** | il *perché*, le decisioni, il razionale | «Perché Postgres», un ADR |
| **Indice / Hub** | non ha contenuto proprio, orchestra altre pagine | «Indice Backend», «Onboarding» |

**Profilo Sertor.** Le aree della tassonomia sono *per natura* (`concepts`/`tech`/`experiments`/`sources`/
`syntheses`) e **tagliano** gli archetipi: l'archetipo è la *forma*, l'area è la *casa* (vedi playbook §3).
Mappatura: Entità/Concetto → `concepts`/`tech`; Spiegazione/razionale → `syntheses` (+ il razionale *datato*
nei record `experiments`); Riferimento → di solito `tech` o una sezione, non un'area a sé; Hub → l'unico hub
è l'`index.md` globale. Sertor **non usa** tutti gli archetipi: non ha how-to operativi nel wiki (le
procedure-strumento vivono in `.claude/`, sono *tooling*) né hub per-area. Va bene: usa solo gli archetipi
che servono, non forzarli.

### La lente di prodotto — quali entità di una **codebase** meritano una pagina

Gli archetipi sopra sono generali; quando l'ospite è **codice** (il caso di Sertor) la domanda «cosa merita
una pagina?» (§1) si specializza. I costrutti del codice che hanno **identità propria** e sono **referenziati
da più punti** diventano pagine-entità; gli altri restano paragrafi dentro la pagina del loro contenitore.

| Costrutto del codice | Archetipo | Area (profilo Sertor) | Esempio |
|---|---|---|---|
| **Entità di dominio** (un tipo del modello) | Entità/Concetto | `concepts` | `Document`, `Chunk`, `RetrievalResult` |
| **Porta / contratto** (Protocol, interfaccia) | Entità/Concetto | `concepts` | `EmbeddingProvider`, `VectorStore` |
| **Adapter / implementazione concreta** | Entità/Concetto | `tech` | adapter Chroma, provider Ollama |
| **Servizio / orchestratore** | Entità/Concetto | `concepts` | dispatcher di chunking, facade di retrieval |
| **Decisione architetturale** (il *perché* di una scelta) | Spiegazione/ADR | `syntheses` (+ datato in `experiments`) | wrapper `_Node`, policy errori non-uniforme |
| **Tecnologia / libreria esterna** | Entità/Concetto | `tech` | `tree-sitter-language-pack` |

**Anti-frammentazione (vale doppio sul codice).** *Non* una pagina per ogni classe o funzione: la gran parte
del codice è dettaglio implementativo, non entità. Il filtro resta §1 — un costrutto diventa pagina solo se
ha un **nome stabile** con cui ci si riferisce ad esso e se **più pagine** avrebbero bisogno di linkarlo. Una
porta sì (la citano l'entità, l'adapter, la composition); un metodo privato no.

**Distillazione (operazione `distill`).** Estrarre queste entità dal record datato di un lavoro — invece di
lasciarle sepolte nel diario di sessione — è il compito dell'operazione `distill` (`ops/distill.md`, parte del
rituale di step): il record `experiment` resta l'**evento** (cosa, quando, esito, puntatori), le entità vivono
in pagine proprie.

## 3. Le pagine di struttura (l'impalcatura)

Non descrivono contenuto: **tengono insieme la rete**.

- **Home** — una *porta d'ingresso*, non un contenitore. Risponde in pochi secondi a «dove sono? cosa c'è
  qui? da dove comincio?»: una frase di scopo, i 4–6 punti d'ingresso principali, le pagine più usate. Non
  lunga, non piena di conoscenza che invecchia.
- **Hub / indice** — uno per grande area; raggruppa e ordina le pagine di quell'area. Livello intermedio tra
  Home e foglie.
- **Overview** — quando un'area è complessa: *racconta* il dominio e poi linka al dettaglio. Differenza
  dall'hub: l'hub è **navigazione** (lista di link), l'overview **spiega** e poi linka.
- **Glossario** — l'àncora dei concetti atomici e ricorrenti, così non li rispieghi ovunque.
- **Categorie / tag** — navigazione **trasversale** che taglia la gerarchia (es. tutte le «deprecato», tutte
  le «security»).

**Profilo Sertor.** `index.md` fa da **home + hub globale** insieme (catalogo con summary per pagina); i
`tags` del frontmatter sono le **categorie** trasversali. Non ci sono ancora hub/overview per-area (la
tassonomia è piatta): se un'area cresce molto, un'overview in `syntheses/` è la mossa naturale.

## 4. I due assi di navigazione (convivono)

Una buona wiki ha **sempre due assi**, non uno:

1. **Gerarchia (albero)** — Home → Hub → Pagina. Dà il senso di **posizione** («dove sono»). Profondità
   ideale **2–3 livelli**, raramente di più: a 5 livelli ci si perde.
2. **Rete (link orizzontali)** — i collegamenti **contestuali** tra pagine. Danno il senso di **relazione**
   («cosa c'entra con cos'altro»).

L'errore classico è averne **uno solo**: solo albero (rigido, devi già sapere dov'è una cosa) o solo rete
(ti perdi, nessun punto fermo).

**Profilo Sertor.** L'albero è **volutamente piatto** — un livello di aree + `index.md` come home/hub — e il
grosso del valore sta nella **rete** dei `[[wikilink]]`. È il senso di «un wiki è un grafo, non un albero»: la
cartella dà solo *una casa*, i link danno il *significato* (la **collocazione** per natura — quale casa — sta
nel playbook §3). Qui la sfumatura: anche un albero piatto è un asse — serve come punto fermo, non va abolito,
solo tenuto basso.

## 5. Igiene a livello wiki

- **Una sola pagina canonica per concetto** (Single Source of Truth). Se la stessa cosa è spiegata in due
  posti, prima o poi divergono: le altre **linkano, non ricopiano**.
- **Niente orfani né dead-end** — ogni nodo dev'essere nella rete; la **disciplina dei link** che lo
  garantisce sta a livello di pagina → [`page-craft.md`](page-craft.md) §4 (gli orfani li trova il lint A).
- **Naming coerente e prevedibile** — convenzioni stabili sui titoli/slug, così si indovina dove sta una
  cosa e come linkarla (profilo Sertor: kebab-case; entità/concetti in inglese — vedi playbook §4).
- **Coerenza > completezza** — meglio poche pagine vive e aggiornate che cento morte: una pagina **obsoleta**
  è peggio di una assente perché tradisce la fiducia (è ciò che il [`page-craft.md`](page-craft.md) chiama
  *verità ancorata* e il lint B difende).
- **Crescita per refactoring, non per accumulo** — quando una pagina diventa troppo grande la spezzi in
  *entità + hub*; quando ci sono troppe micro-pagine le **fondi**. La struttura è viva, va potata come un
  giardino (è l'operazione `reorg`).

## Il modello mentale

Pensa alla wiki come a un **grafo con un'impalcatura**:

- **Nodi-contenuto** (entità, how-to, reference, spiegazioni) = il sapere → uno per concetto, del tipo giusto.
- **Nodi-struttura** (home, hub, overview, glossario, categorie) = l'impalcatura che rende il sapere
  *trovabile*.
- **Link** = il tessuto connettivo, su due assi: **gerarchia** (dove sono) + **rete** (cosa c'entra).
- **La regola d'oro del *quando*:** crea una pagina quando una cosa ha un **nome stabile** ed è
  **referenziata da più punti**.
