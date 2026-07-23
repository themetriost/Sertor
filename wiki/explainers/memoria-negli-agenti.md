---
title: La memoria della conversazione (in parole semplici)
type: explainer
tags: [non-tecnici, memoria, conversazioni, archivio, privacy, spiegazione]
created: 2026-06-14
updated: 2026-07-23
sources: ["wiki/concepts/memoria-conversazioni.md", "wiki/tech/transcript-capture-adapter-e-storage.md", "requirements/memoria-conversazioni/epic.md", "requirements/memoria-conversazioni/ricerca-semantica/requirements.md"]
---

# La memoria della conversazione — quello che non si dimentica

Quando lavori con Sertor su un progetto, avviene una conversazione: tu fai domande, l'assistente risponde, si discutono decisioni, si genera codice. Poi la finestra si chiude.

**Cosa succede di solito?** La conversazione scompare. Se la prossima settimana devi tornare a una decisione presa, non c'è più il contesto. Ricominci da zero.

## La metafora

Immagina un **registratore che accendi quando lavori**: ogni volta che parli con l'assistente, il registratore cattura la conversazione e la mette in una **scatola conservata** (un archivio locale sul tuo computer). Le registrazioni non si cancellano da sole, restano lì. Se un giorno dici "attendi, dove avevamo detto di mettere quella logica?", il registratore sa dove cercare — in quella conversazione del 2 giugno.

Però il registratore è **intelligente**: se per errore dici la tua password durante la conversazione (cosa che succede), il registratore **non la conserva** — la sostituisce con `[SEGRETO]` prima di metterla nella scatola.

## Che cosa conserva

L'archivio conserva:

- **La conversazione intera** — chi ha detto che cosa, in ordine.
- **Il timestamp** — quando è stata la conversazione.
- **Il contesto** — quale progetto, quale sessione.
- **I turni della conversazione** — dove finisce una frase e inizia l'altra (importerà fra poco quando cercherai in quell'archivio).

**Cosa NON conserva:**
- I segreti (password, chiavi API) — sostituiti con `[SEGRETO]`.
- Niente di cui non hai detto esplicitamente "attiva la memoria".

## Come funziona

1. **Disattivato di default** — finché non lo dici, non viene salvato nulla.
2. **Quando lo attivi** (linea nel `.env`: `SERTOR_MEMORY=true`), il sistema fa due cose:
   - **Cattura automatica a fine sessione:** ogni volta che chiudi una conversazione con l'assistente, il nostro hook salva silenziosamente il transcript nel database.
   - **Database locale:** `<cartella-del-progetto>/.sertor/memory.sqlite`, escluso da git.
3. **Idempotente** — se il sistema legge la stessa sessione due volte, non crea duplicati. Una sessione = un record.
4. **Conservato** — non si cancella da solo, se non glielo dici.

## Perché serve

- **Ritornare al contesto** — se dimandi "dove avevamo detto di mettere quella logica", il sistema sa cercare tra le vecchie conversazioni e trovare il turno giusto.
- **Ricerca nel passato** — FATTO (FEAT-002): puoi dire "trovami una conversazione dove abbiamo discusso di autenticazione" e il sistema esegue una ricerca testuale locale nelle conversazioni passate.
- **Ricerca per significato** — FATTO (FEAT-004): puoi cercare un *concetto* anche se non ricordi le parole esatte (vedi sotto, "Cercare per parola, o per significato").
- **Ricerca temporale** — se ricordi vago ("tre settimane fa"), puoi limitare la ricerca a quel periodo.
- **Fonte grezza per il wiki** — FATTO (FEAT-003): il wiki distilla la conoscenza, ma l'archivio tiene il grezzo. Ora, se una decisione importante non è mai finita nel wiki, puoi **recuperare quella conversazione intera** (`sertor-rag memory show`) e distillarla a posteriori — invece di ricostruirla a memoria. Con una regola precisa: si recupera **una conversazione mirata, quando lo chiedi tu** — mai si rimastica l'intero archivio da solo (sarebbe uno spreco). La scatola è un *backup*, non qualcosa che gira di continuo.
- **Prova** — se qualcuno chiede "su cosa vi siete decisi?", hai una traccia immutabile.

## Cercare per parola, o per significato

Fino a ieri la ricerca trovava solo le **parole esatte**: cercavi «memoria» e trovavi i turni che contenevano la parola «memoria». Ma se in quella conversazione avevi parlato di «archivio», «storage» o «ricordare le sessioni» — stesso argomento, parole diverse — non li trovavi.

Pensa alla differenza tra **cercare un libro per titolo** e **cercarlo per argomento**:
- *Per parola* (ricerca testuale, il default): trovi solo i libri il cui titolo contiene esattamente quella parola. Veloce, preciso, ma cieco ai sinonimi.
- *Per significato* (ricerca semantica, novità FEAT-004): il bibliotecario capisce **di cosa parli** e ti porta anche i libri che trattano l'argomento con altre parole.

Da oggi puoi scegliere il secondo modo aggiungendo `--semantic`:
```bash
sertor-rag memory search "come gestiamo i ricordi delle sessioni" --semantic
```
e il sistema ti riporta i turni **di significato affine**, anche se non usano le tue stesse parole.

Due cose importanti, entrambe per la tua tranquillità:
- **La ricerca per parola resta il default.** Quella per significato la chiedi tu, esplicitamente, quando serve. Niente cambia se non lo chiedi.
- **Resta sul tuo computer.** Per capire il significato, il sistema deve "tradurre" le conversazioni in numeri (gli *embedding*). Con il motore locale (l'impostazione predefinita) questo avviene **interamente sulla tua macchina** — niente lascia il computer. È un interruttore separato e spento di default (`SERTOR_MEMORY_SEMANTIC=true`), proprio perché è un'operazione in più sul contenuto.

E lo fa **senza rifare ogni volta tutto il lavoro**: ogni conversazione viene "tradotta" una sola volta, al momento in cui la chiudi. Le vecchie non vengono ri-elaborate (l'archivio non cambia mai il passato), quindi il costo resta basso e proporzionato solo alle conversazioni nuove.

## Quello che succede dietro le quinte

1. **Cattura automatica (FEAT-001)** — quando chiudi una conversazione con l'assistente (Claude Code **o** GitHub Copilot CLI, FEAT-008), un **hook automatico** cattura il transcript SENZA che tu debba far nulla. È silenzioso e non blocca il flusso (se qualcosa fallisce, continua comunque).
2. **Ripulitura** — prima di mettere la conversazione nell'archivio, il sistema scandisce il testo e sostituisce i segreti con marcatori (`sk-abc → [SEGRETO: openai_key]`). Non resta nulla in chiaro.
3. **Archiviazione** — la conversazione ripulita finisce in una tabella SQL locale. Non va su cloud, resta sul tuo computer, esclusa da git.
4. **Ricerca da terminale (FEAT-002)** — quando fai una domanda come "trovami una conversazione su X", usi il comando da terminale:
   ```bash
   sertor-rag memory search "X"
   ```
   Il sistema esegue una ricerca **testuale locale** (senza rete, senza IA) nell'archivio e restituisce i turni che corrispondono, con la sessione e il momento. *(Dal 2026-07-20 l'assistente può anche interrogare l'archivio **direttamente**, senza terminale, tramite i suoi strumenti nativi — i tool MCP `memory_search`/`memory_list`/`memory_show`, FEAT-010.)*

## Privacy

- **Disattivato di default.** Se non lo accendi, niente viene archiviato. Zero.
- **Ripulito dai segreti.** Se per errore dici una password, il registratore non la salva.
- **Locale.** L'archivio risiede sul tuo computer, non su un server.
- **Opt-in.** Una linea nel `.env` (`SERTOR_MEMORY=true`) per accenderlo esplicitamente.

## Limitazioni attuali

- **Ricerca per significato: qualità legata al motore locale.** Ora puoi cercare per significato (FEAT-004), ma con il motore locale (predefinito, privacy-safe) la "comprensione" è più semplice di quella di un grande modello cloud: i risultati per significato sono utili ma non perfetti. È un compromesso voluto tra qualità e privacy — la scelta del motore resta tua.
- **Segreto dimenticato?** Il sistema riconosce i pattern comuni (chiavi OpenAI, token AWS, password), ma se un segreto è in un formato strano, il sistema potrebbe non riconoscerlo. Se pensi di aver detto qualcosa di sensibile, disattiva la memoria.

## Come attivarlo

1. Aggiungi al tuo `.env`:
   ```
   SERTOR_MEMORY=true
   ```

2. Al prossimo uso, il sistema inizia a **catturare automaticamente** le conversazioni a fine sessione (senza che tu faccia nulla).

3. Per cercare nelle conversazioni passate, dal terminale:
   ```bash
   sertor-rag memory search "argomento che cerchi"
   sertor-rag memory search "GraphRAG" --since 2026-06-01  # con filtro temporale opzionale
   ```

4. *(Opzionale)* Per la ricerca **per significato**, aggiungi un secondo interruttore al `.env`:
   ```
   SERTOR_MEMORY_SEMANTIC=true
   ```
   poi cerca con `--semantic`:
   ```bash
   sertor-rag memory search "come gestiamo i ricordi delle sessioni" --semantic
   ```
   Le conversazioni già archiviate prima di accendere l'interruttore si recuperano una volta con
   `sertor-rag memory index-semantic` (backfill).

## Il futuro

- **Marcare i turni importanti** (FEAT-005) — dire "ricorda questo turno" per segnalarlo come importante.
- **Retention** (FEAT-006) — governance dell'archivio: decidere quando i turni vanno in scadenza.

*(Il **multi-assistente** non è più «futuro»: dal 2026-06-22 il registratore cattura anche su **GitHub
Copilot CLI**, non solo Claude Code — FEAT-008 consegnata.)*

---

## Approfondimento tecnico

- [[memoria-conversazioni]] — il concetto e il tier episodico della memoria.
- [[transcript-capture-adapter-e-storage]] — come si catturano e si archiaviano i transcript.
- [[ricerca-episodica-fts5]] — il motore FTS5 che fa funzionare la ricerca locale.
