# Come si scrive una pagina ben fatta — anatomia del page-craft

> **Pagina di riferimento (foglia).** Descrive *com'è fatta una buona pagina del wiki* — struttura,
> contenuto, significato, link. È **linkata da** chi crea o riscrive pagine (`ops/record.md`,
> `ops/ingest.md`, `ops/query.md`, e il giudizio di `ops/lint.md` livello C e `ops/reorg.md`). È una
> **foglia**: non dipende da altri documenti del sistema — le operazioni la referenziano, non viceversa.
>
> **Host-agnostica (Principio X).** I principi qui valgono su qualunque host; ciò che *varia* — campi del
> frontmatter, sintassi dei link, e l'esistenza di costrutti come TOC automatico, tag, stato/owner, redirect
> o gerarchie genitore/figlio — viene dal profilo dell'ospite (`wiki.config.toml`) e dalle capacità
> dell'host. Gli esempi concreti (`[[wikilink]]`, `concepts/`, `title/type/tags…`) sono il **profilo
> Sertor**, non leggi universali: su un altro progetto cambia solo la resa, non i principi.

Una pagina ben fatta ha quattro qualità: una **struttura** prevedibile, **contenuto** azionabile, il giusto
**livello di significato**, e **link** densi. Le prime due sono forma, il significato è sostanza, i link
sono ciò che trasforma un insieme di pagine in una *wiki*.

## 1. Struttura della pagina (dall'alto in basso)

1. **Titolo univoco** — descrive **una** cosa. Niente titoli vaghi ("Note", "Varie") né doppioni con altre
   pagine (il naming kebab-case e l'unicità sono verificabili meccanicamente, lint A).
2. **Lead (apertura)** — in 1–3 righe risponde a «di cosa parla questa pagina?» **senza presupporre** che il
   lettore abbia letto altro. Deve reggere da solo: è spesso l'unica cosa che viene letta, ed è il primo
   chunk che il RAG recupera *fuori contesto*. Apri con «**X è …**», non con «Questo concetto è stato visto
   in…».
3. **Indice (TOC)** — *se l'host lo genera* (Obsidian, MediaWiki…) e la pagina supera ~3–4 sezioni. Nei wiki
   a soli file Markdown è opzionale.
4. **Corpo a sezioni** con heading **gerarchici reali** (H2 per le sezioni principali, H3 per le
   sotto-sezioni): la gerarchia riflette il contenuto, non è decorativa.
5. **"Vedi anche" / correlati** in fondo — *supplemento* di navigazione (vedi §4: non sostituisce i link
   inline).
6. **Riferimenti / fonti** se la pagina afferma fatti verificabili (profilo Sertor: campo frontmatter
   `sources`).
7. **Metadati** — il frontmatter coi campi attesi dal profilo (`frontmatter_required`/`_optional` in
   config; profilo Sertor: `title`, `type`, `tags`, `created`, `updated`, `sources`). Campi come stato
   (bozza/in revisione/stabile) o owner **solo se** l'host/profilo li prevede.

## 2. Tipo di contenuti

- **Una pagina = un concetto.** Se ti accorgi di descrivere due argomenti distinti, sono **due pagine**
  collegate, non una. Le pagine atomiche si linkano meglio, si riusano in più contesti e si **chunkano
  puliti** per il RAG. Criterio di **split**: due "cos'è" distinti → due pagine con wikilink reciproci. Sotto
  la pressione dell'append è qui che si cede (sezioni duplicate, due blocchi di stato): *ricuci o splitta*,
  non appendere.
- **Piramide rovesciata** — prima l'informazione più importante, poi i dettagli, poi i casi limite. Il
  lettore deve poter fermarsi a metà e aver già capito l'essenziale.
- **Concreto e azionabile** — esempi, snippet, comandi, tabelle. Una procedura va scritta come **lista
  numerata** di passi.
- **Auto-contenuta ma non ridondante** — spiega il necessario, ma per i concetti che hanno già una loro
  pagina **linka, non ricopiare**: l'informazione duplicata invecchia in due posti diversi.
- **Stile neutro e diretto** — frasi brevi, voce attiva, niente muri di testo; elenchi e tabelle quando i
  dati sono strutturati.
- **Aggiornabilità** — le informazioni che cambiano (versioni, owner, URL) vanno in **un punto solo e ben
  visibile**.

## 3. Il livello di significato — *cosa* scrivere, non solo come

È la sostanza, oltre alla forma. Una pagina cattura **conoscenza distillata e riusabile**, non la cronaca di
ciò che è successo (quella sta nel log). Scrivi perché un **LLM futuro**, che la recupera *a freddo* via RAG,
possa agire su di essa.

- **Distilla, non trascrivere.** La pagina risponde a «cosa serve sapere a chi riprende», non «cosa abbiamo
  fatto passo-passo». Il diario cronologico è il log; la pagina è ciò che *resta*.
- **Cattura il *perché* e le alternative scartate.** Una decisione senza razionale e senza le opzioni
  rifiutate verrà **ri-litigata**. Scrivi: cosa si è deciso · perché · cosa si è scartato e perché.
- **Astrazione coerente con l'area.** Una pagina `concept`/`tech` è **evergreen**: il claim centrale è
  atemporale, **niente stato volatile** (PR#, "in corso", conteggi) nel corpo — invecchia e diventa deriva
  (lint B). Lo stato datato vive in `experiments`. Il *perché* generalizza; il *cosa* situato sta nel record.
- **Verità ancorata.** Scrivi solo claim **veri al momento della scrittura e ancorabili** (codice/test/git/
  fonte). Ciò che non puoi fondare non è contenuto: è un'ipotesi → marcala come tale (è il rovescio attivo
  del lint B).
- **Densità di significato.** Ogni frase porta informazione; taglia il filler. *Compila una volta*: scrivi
  perché non vada riscritta.

*Esempio — la stessa nozione, scritta male → bene:*
- ✗ «Oggi abbiamo discusso a lungo del reranking e alla fine, dopo vari tentativi, abbiamo deciso di usare il
  cross-encoder che sembrava andare meglio degli altri nei test.» — *diario, vago, non ancorato, nessun
  perché riusabile.*
- ✓ «Il **reranking cross-encoder** ri-ordina i top-k del retrieval valutando la coppia (query, chunk)
  insieme: più accurato del bi-encoder ma costa O(k) inferenze → si applica **solo ai candidati**, non
  all'indice. Preferito a BM25+rerank perché [motivo]; scartato il reranking LLM-as-judge per latenza/costo
  sproporzionati al guadagno.» — *definisce, dà il trade-off e il perché, è atemporale e ancorabile.*

## 4. Tipo di link

I link sono ciò che trasforma un insieme di pagine in una vera wiki. Tre categorie utili, **distinte**:

- **Interni contestuali** — la **prima volta** che citi un concetto che ha una sua pagina, collegalo
  **inline** nel testo (profilo Sertor: `[[nome-pagina]]`; alias con `[[nome-pagina|testo mostrato]]`). Linka
  la **prima occorrenza**, non tutte. È qui che sta il valore: il link contestuale dice *perché* due pagine
  sono connesse.
- **Navigazione strutturale** — "Vedi anche", categorie/tag, e — *dove l'host ha gerarchie* — pagine
  genitore/figlie. Nel modello a **grafo** (non albero) di questo wiki: wikilink + aree di tassonomia.
  Servono a esplorare il vicinato della pagina. **Non** sostituiscono i link contestuali: relegare tutti i
  link in una sezione finale invece che inline è uno *smell* organizzativo (lint C).
- **Esterni / riferimenti** — fonti, documentazione ufficiale, ticket, RFC: in una **sezione dedicata** o
  come note, **non** mescolati al testo come quelli interni.

Regole pratiche sui link:
- Il **testo del link descrive la destinazione** («vedi la guida al deploy»), mai «clicca qui».
- **Niente orfani né dead-end:** ogni pagina dovrebbe essere raggiungibile da almeno un'altra e a sua volta
  puntare a qualcosa (gli orfani li trova il lint A).
- **Forward-link → crea uno *stub*.** Linkare in avanti un nodo **non ancora scritto** è una *feature* (marca
  un nodo da creare), ma **non** lasciare un `[[…]]` a vuoto: il lint A lo segnalerebbe come **broken** (per
  lo strumento un target inesistente è indistinguibile da un refuso). Realizza invece il nodo come **stub** —
  un **file reale** nell'area giusta, con frontmatter completo, `status: stub` e un corpo segnaposto
  `> 🚧 STUB`. Così il link **risolve** (lint A verde) e il nodo è *voluto*; al contrario un `[[…]]` senza
  pagina né stub resta **broken** — è così che si separa il **nodo intenzionale** dal **refuso**. Lo stub ha
  ≥1 link entrante (quello che l'ha motivato) → non è orfano; **riempilo appena possibile** (uno stub
  lasciato a lungo è uno *smell* del lint C).
- **Non sovra-linkare:** troppi link rendono il testo illeggibile e svuotano di valore quelli importanti
  (densità ≠ qualità). Preferisci link **specifici** alla pagina giusta, non a pagine-contenitore.
- **Niente link circolari inutili** né — *dove l'host ha i redirect* — redirect a catena.

## Checklist veloce

| Criterio | Domanda da farsi |
|---|---|
| Titolo | È univoco e descrive una sola cosa? |
| Lead | Le prime righe spiegano tutto da sole? |
| Struttura | Heading gerarchici (+ TOC se l'host lo genera)? |
| Scope | Un concetto per pagina? |
| Contenuto | Esempi concreti, piramide rovesciata? |
| Significato | Distilla il *perché* + alternative; claim ancorato e atemporale? |
| Link interni | Prima occorrenza linkata, testo descrittivo? |
| Navigazione | "Vedi anche" + categorie/tag, senza relegare i link inline? |
| Fonti | Le affermazioni verificabili hanno riferimenti? |
| Manutenzione | Stato/owner/data visibili (se previsti)? Niente duplicazioni? |
