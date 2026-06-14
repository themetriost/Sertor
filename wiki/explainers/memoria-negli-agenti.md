---
title: La memoria della conversazione (in parole semplici)
type: explainer
tags: [non-tecnici, memoria, conversazioni, archivio, privacy, spiegazione]
created: 2026-06-14
updated: 2026-06-14 (+ FEAT-003: la distillazione attinge all'archivio — `memory show`/`list`, loop cattura→distill chiuso) · 2026-06-14 (+ FEAT-035: superficie CLI + hook SessionEnd, MVP completo)
sources: ["wiki/concepts/memoria-conversazioni.md", "wiki/tech/transcript-capture-adapter-e-storage.md", "requirements/memoria-conversazioni/epic.md"]
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
- **Ricerca temporale** — se ricordi vago ("tre settimane fa"), puoi limitare la ricerca a quel periodo.
- **Fonte grezza per il wiki** — FATTO (FEAT-003): il wiki distilla la conoscenza, ma l'archivio tiene il grezzo. Ora, se una decisione importante non è mai finita nel wiki, puoi **recuperare quella conversazione intera** (`sertor-rag memory show`) e distillarla a posteriori — invece di ricostruirla a memoria. Con una regola precisa: si recupera **una conversazione mirata, quando lo chiedi tu** — mai si rimastica l'intero archivio da solo (sarebbe uno spreco). La scatola è un *backup*, non qualcosa che gira di continuo.
- **Prova** — se qualcuno chiede "su cosa vi siete decisi?", hai una traccia immutabile.

## Quello che succede dietro le quinte

1. **Cattura automatica (FEAT-035)** — quando chiudi una conversazione con Claude Code, un **hook automatico** cattura il transcript SENZA che tu debba far nulla. È silenzioso e non blocca il flusso (se qualcosa fallisce, continua comunque).
2. **Ripulitura** — prima di mettere la conversazione nell'archivio, il sistema scandisce il testo e sostituisce i segreti con marcatori (`sk-abc → [SEGRETO: openai_key]`). Non resta nulla in chiaro.
3. **Archiviazione** — la conversazione ripulita finisce in una tabella SQL locale. Non va su cloud, resta sul tuo computer, esclusa da git.
4. **Ricerca da terminale (FEAT-035)** — quando fai una domanda come "trovami una conversazione su X", usi il comando da terminale:
   ```bash
   sertor-rag memory search "X"
   ```
   Il sistema esegue una ricerca **testuale locale** (senza rete, senza IA) nell'archivio e restituisce i turni che corrispondono, con la sessione e il momento.

## Privacy

- **Disattivato di default.** Se non lo accendi, niente viene archiviato. Zero.
- **Ripulito dai segreti.** Se per errore dici una password, il registratore non la salva.
- **Locale.** L'archivio risiede sul tuo computer, non su un server.
- **Opt-in.** Una linea nel `.env` (`SERTOR_MEMORY=true`) per accenderlo esplicitamente.

## Limitazioni attuali

- **Ricerca solo testuale.** Per ora il sistema cerca per parole chiave e frasi (ricerca testuale), non per significato. Una ricerca «memoria» non troverà turni che parlano di «storage» sebbene il significato sia correlato (estensione semantica: FEAT-004).
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

## Il futuro

- **Ricerca semantica** (FEAT-004) — estensione: "trovami conversazioni di significato correlato a X" (con embedding, opt-in separato).
- **Marcare i turni importanti** (FEAT-005) — dire "ricorda questo turno" per segnalarlo come importante.
- **Retention** (FEAT-006) — governance dell'archivio: decidere quando i turni vanno in scadenza.
- **Multi-assistente** (FEAT-008) — il registratore funzionerà anche con altri assistenti, non solo Claude Code.

---

## Approfondimento tecnico

- [[memoria-conversazioni]] — il concetto e il tier episodico della memoria.
- [[transcript-capture-adapter-e-storage]] — come si catturano e si archiaviano i transcript.
- [[ricerca-episodica-fts5]] — il motore FTS5 che fa funzionare la ricerca locale.
