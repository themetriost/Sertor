---
title: La memoria della conversazione (in parole semplici)
type: explainer
tags: [non-tecnici, memoria, conversazioni, archivio, privacy, spiegazione]
created: 2026-06-14
updated: 2026-06-14
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
2. **Quando lo attivi**, il sistema guarda all'interno della cartella dove Claude Code già mette i file di sessione (`~/.claude/projects/`), li legge, li ripulisce dai segreti, e li mette in un **database locale** (`<cartella-del-progetto>/.sertor/memory.sqlite`, escluso da git).
3. **Idempotente** — se il sistema legge la stessa sessione due volte, non crea duplicati. Una sessione = un record.
4. **Conservato** — non si cancella da solo, se non glielo dici.

## Perché serve

- **Ritornare al contesto** — se dimandi "dove avevamo detto di mettere quella logica", il sistema sa cercare tra le vecchie conversazioni.
- **Ricerca nel passato** — a breve sarà possibile dire "trovami una conversazione dove abbiamo discusso di autenticazione".
- **Fonte grezza** — il wiki distilla la conoscenza, ma l'archivio tiene il grezzo. Se una pagina del wiki è incomplete, l'archivio sa dove cercare.
- **Prova** — se qualcuno chiede "su cosa vi siete decisi?", hai una traccia immutabile.

## Quello che succede dietro le quinte

1. **Cattura** — ogni volta che parli con Claude Code, il sistema sa che sta salvando la sessione. Il nostro sistema legge quelle sessioni.
2. **Ripulitura** — prima di mettere la conversazione nell'archivio, il sistema scandisce il testo e sostituisce i segreti con marcatori (`sk-abc → [SEGRETO: openai_key]`). Non resta nulla in chiaro.
3. **Archiviazione** — la conversazione ripulita finisce in una tabella SQL locale. Non va su cloud, resta sul tuo computer, esclusa da git.
4. **Attesa di ricerca** — il grosso del valore arriverà quando potrai **cercare** in questo archivio (feature successiva).

## Privacy

- **Disattivato di default.** Se non lo accendi, niente viene archiviato. Zero.
- **Ripulito dai segreti.** Se per errore dici una password, il registratore non la salva.
- **Locale.** L'archivio risiede sul tuo computer, non su un server.
- **Opt-in.** Una linea nel `.env` (`SERTOR_MEMORY=true`) per accenderlo esplicitamente.

## Limitazioni attuali

- **Non puoi cercarlo ancora.** Per adesso il sistema archivia, ma la ricerca viene dopo (FEAT-002).
- **Segreto dimenticato?** Il sistema riconosce i pattern comuni (chiavi OpenAI, token AWS, password), ma se un segreto è in un formato strano, il sistema potrebbe non riconoscerlo. Se pensi di aver detto qualcosa di sensibile, disattiva la memoria.

## Come attivarlo

Aggiungi al tuo `.env`:
```
SERTOR_MEMORY=true
```

Al prossimo uso, il sistema inizia a leggere e archiviare le conversazioni.

## Il futuro

- **Ricerca episodica** (FEAT-002) — "trovami conversazioni su X" (ricerca testuale, senza IA).
- **Distillazione** — il sistema attingerà dall'archivio per migliorare il wiki.
- **Multi-assistente** — il registratore funzionerà anche con altri assistenti, non solo Claude Code.

---

## Approfondimento tecnico

Vedi [[memoria-conversazioni]] per il concetto, [[transcript-capture-adapter-e-storage]] per le componentitecniche.
