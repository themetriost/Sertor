---
title: Una pratica standing non è una pratica distribuita
type: concept
tags: [fedelta-dogfood, principio-x, asset-host-facing, problema-aperto, e15, governance]
created: 2026-07-29
updated: 2026-07-29
sources: ["CLAUDE.md", "packages/sertor/src/sertor_installer/assets/claude-md-block.md", "requirements/fedelta-dogfood/epic.md", "wiki/log/2026-07-28.md", "wiki/log/2026-07-29.md"]
---

# Una pratica standing non è una pratica distribuita

> **⚠️ Problema aperto, non soluzione.** Il rimedio **non esiste**: la sua forma è indecisa, e la pagina
> spiega **perché** è difficile invece di fingere che basti una guardia. Esiste perché il candidato è
> stato **dichiarato e rinviato due volte** (28 e 29/07) e alla terza il rinvio diventa un modo per non
> decidere — la stessa regola già applicata a [[riassunto-invecchia-senza-riconciliatore]]. Casa del
> rimedio: **E15-FEAT-011**.

Una pratica di lavoro può essere **vincolante per noi** e **inesistente per gli ospiti**, e nulla
confronta le due cose.

> **La firma:** la pratica funziona benissimo — la si applica ogni giorno, produce risultati, entra nei
> record. È **vera**, solo non è **spedita**. E siccome noi la vediamo funzionare, nessuno pensa a
> chiedersi se qualcun altro ce l'abbia.

## L'istanza che ha aperto il caso

Il 2026-07-28 la **regola del boy scout** è stata resa standing scrivendola al punto 10 del rituale in
`CLAUDE.md` — cioè nella **prosa dogfood italiana**. Il giorno dopo, alla domanda dell'utente *«quindi
la regola del boy scout non c'è»*, la verifica: il blocco `SERTOR:WIKI-RITUAL` del dogfood era
**byte-identico** all'asset distribuito, e la regola **non c'era**, né lì né in nessun ospite.

**È la regola 1 del `CLAUDE.md` violata nel file che la enuncia:**

> *«Una feature è completa SOLO se è installabile su un ospite. […] se vive solo nel `.claude/`/`.env` di
> Sertor, è un prototipo, non una feature.»*

La regola c'era. L'enforcement no.

## Perché i due livelli di E15 non la vedono

[[dogfood-fidelity]] presidia due assi, e **quel giorno erano entrambi perfetti**:

| Asse | Domanda | Esito nel caso reale |
|---|---|---|
| **Asset-fidelity** | il dogfood ha *gli stessi file* dell'ospite? | ✅ blocco byte-identico all'asset |
| **Process-fidelity** | il dogfood è *prodotto dai veri installer*? | ✅ depositato dall'install reale |
| **↯ terzo asse** | *ciò che facciamo* è anche *ciò che spediamo*? | ❌ **nessuno lo guarda** |

Il difetto sta **fuori** dal perimetro di entrambi: la pratica non era *nel file sbagliato*, era **in un
file che non viaggia**. Una guardia di identità byte non può rilevare l'assenza di qualcosa che non è
mai stato scritto dove sarebbe stato confrontato.

## Perché il rilevatore è difficile (ed è il motivo per cui resta aperto)

Confrontare «prosa dogfood» con «blocco distribuito» **non è un diff**:

- **Sono in lingue diverse** — la prosa è italiana, i blocchi sono inglesi *per costruzione* (contratto
  client-form generico).
- **Sono a granularità diversa** — la prosa **elabora**, localizza e arricchisce; il blocco è la forma
  essenziale. Molte righe non hanno una controparte, **e va bene così**.
- **La divergenza è voluta e dichiarata** — il `CLAUDE.md` ha una sezione apposta (*«Blocchi installati
  vs prosa dogfood»*) che spiega perché il file è bilingue e ordina di **non riconciliare** cancellando
  la prosa. Un rilevatore ingenuo segnalerebbe come difetto l'intero design.
- **La prosa è un super-set legittimo** — contiene regole **dogfood-only per decisione** (il re-lock del
  runtime, l'archiviazione delle richieste processate): la loro assenza dai blocchi è **corretta**, non
  un buco.

> Il rilevatore deve distinguere *«non distribuita perché ce ne siamo dimenticati»* da *«non distribuita
> perché non deve esserlo»*. Quella distinzione è **giudizio**, e un rilevatore che la sbaglia produce
> un contatore stabilmente diverso da zero — che è il difetto già visto altrove: una guardia rumorosa
> smette di essere letta.

## Tre forme possibili, nessuna decisa

1. **Inventario dichiarato.** Ogni pratica standing porta un campo esplicito *distribuita: sì/no/perché*.
   Il controllo diventa meccanico (ogni voce ha il campo?) e il giudizio resta dov'è: nella
   compilazione. Costo: una copia in più da tenere allineata — cioè
   [[riassunto-invecchia-senza-riconciliatore]] applicato all'inventario stesso.
2. **Momento del rituale.** Quando uno step **aggiunge una regola standing**, il rituale chiede *«va
   distribuita?»* e pretende un verdetto dichiarato. Non rileva nulla: costringe a **decidere**, come il
   pavimento del distill. Costo: dipende dall'onestà dell'agente — la cosa che è già fallita qui.
3. **Guardia al tocco dell'asset.** Chi edita la prosa del rituale riceve un promemoria: *questo blocco
   ha un gemello distribuito*. Deterministica e cieca al contenuto, quindi senza falsi positivi — ma
   scatta solo quando si tocca il file giusto, e questo caso è nato **proprio** toccando quel file.

*(La 3 non avrebbe salvato il caso reale: la prosa e il blocco sono nello **stesso** file `CLAUDE.md`.)*

## Cosa dice il caso, al di là del rimedio

L'ha colta **l'utente, non uno strumento** — e non una guardia, un test o un lint. La domanda che l'ha
scoperta era di tre parole: *«quindi non c'è»*.

> **Le pratiche nascono nella prosa**, perché è lì che si scrive mentre si ragiona. La distribuzione è un
> **secondo atto**, e un secondo atto che nessuno reclama non avviene.

## Vedi anche

- [[dogfood-fidelity]] — i due assi che questo caso mostra insufficienti.
- [[riassunto-invecchia-senza-riconciliatore]] — la gemella: là una copia invecchia, qui una copia **non
  viene mai fatta**. Entrambe sono Principio XIV (*derivare, o dichiarare la divergenza*).
- [[step-ritual]] — dove vivrebbe la forma 2.
- [[deterministic-vs-judgment]] — perché il rilevatore ingenuo non funziona: la distinzione
  «dimenticata» vs «volutamente locale» è giudizio.
- [[constitution]] — Principio X (host-agnostico) e XIV.
