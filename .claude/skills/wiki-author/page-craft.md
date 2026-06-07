# Come si scrive una pagina ben fatta — anatomia del page-craft

> **Pagina di riferimento (foglia).** Descrive *cosa rende buona una pagina del wiki* — struttura e
> significato. È **linkata da** chi crea o riscrive pagine (`ops/record.md`, `ops/ingest.md`, e il giudizio
> di `ops/lint.md` livello C e `ops/reorg.md`). Non dipende dal playbook: è un'unità di conoscenza a sé, così
> le operazioni la referenziano senza creare dipendenze circolari.
>
> Per il *formato* (frontmatter, naming, wikilink) vedi il playbook §4; per *dove* vive una pagina (area per
> natura) vedi il playbook §3. Qui si parla di **com'è fatta dentro**.

Quattro proprietà, dalla forma alla sostanza. Le prime tre sono **struttura**, l'ultima è **significato** —
ed è quella che conta di più.

## 1. Atomicità — una pagina, un concetto

È la regola più importante per un LLM Wiki: pagine atomiche si linkano meglio, si riusano in più contesti e
si **chunkano puliti** per il RAG (una pagina che parla di tre cose produce chunk ambigui e link generici).
Criterio di **split**: se sviluppando una pagina emergono **due focus distinti** (due "cos'è"), crea **due
pagine** collegate da wikilink reciproci invece di accatastare. Sotto la pressione dell'append è qui che si
cede — sezioni duplicate ("Note di processo" ×2, due blocchi di stato) sono il sintomo: *ricuci o splitta*,
non appendere.

## 2. Auto-contenimento — la prima frase definisce

Il RAG recupera una pagina **fuori dal suo contesto**: la **prima frase** deve dire *cos'è* il soggetto
senza presupporre nulla ("**X è …**"), prima dei dettagli — il primo chunk dev'essere autosufficiente. Evita
aperture che rimandano ("Questo concetto è stato approfondito in…").

## 3. Link densi, inline e bidirezionali

Quasi tutto il valore di un wiki sta nei **link**, non nelle cartelle. Linka **al punto di menzione**
(inline), non in una sezione "vedi anche" in fondo: il link contestuale dice *perché* due pagine sono
connesse. Preferisci link **specifici** alla pagina giusta piuttosto che a pagine-contenitore (densità ≠
qualità). I `[[wikilink]]` danno i **backlink** gratis (segnale di rilevanza per umano e RAG); una pagina
**orfana** (zero link entranti) è invisibile alla navigazione — è uno *smell*, falla linkare. Linkare in
avanti una pagina **non ancora esistente** è una *feature* (marca un nodo da creare), non un errore.

## 4. Il livello di significato — *cosa* scrivere, non solo come

Le tre regole sopra sono la *forma*; questa è la *sostanza*. Una pagina cattura **conoscenza distillata e
riusabile**, non la cronaca di ciò che è successo (quella sta nel log). Scrivi perché un **LLM futuro**, che
la recupera *a freddo* via RAG, possa agire su di essa.

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
