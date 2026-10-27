# Il confine fra skill e runtime

Una skill è testo che un agente legge e segue. Ogni regola che contiene la tiene il giudizio dell'agente,
che può cedere. Un runtime è codice deterministico: ciò che fa, lo fa sempre. Questo passo decide, regola
per regola, che cosa resta promessa e che cosa diventa costruzione.

## Come si riconosce il lavoro da spostare nel runtime

Quattro famiglie di lavoro sono quasi sempre deterministiche, e nel testo diventano promesse fragili:

| Famiglia | Segnale nel testo della skill | Esempio |
|---|---|---|
| **Estrarre** | "raccogli…", "elenca tutti i…", "leggi da…" | i simboli toccati da un diff, i commit di un intervallo |
| **Verificare** | "controlla che…", "assicurati che…", "verifica…" | che un'àncora punti a righe che esistono, che un file sia valido per uno schema |
| **Nascondere** | "non mostrare…", "tieni nascosto…", "non rivelare…" | i criteri di valutazione di un esercizio |
| **Tenere stato** | "ricorda…", "tieni traccia di…", "alla prossima volta…" | i buchi di uno studente fra una sessione e l'altra |

Se una regola rientra in una di queste famiglie e un errore costerebbe caro, proponi di spostarla.

## Esempi reali di Sinthari

- **La verifica delle àncore di SpecLift.** "Ogni requisito deve citare righe che esistono" scritto come
  regola cede: un agente scrive un'àncora plausibile ma inesistente. Il runtime la riverifica sul
  filesystem, e un'àncora falsa non passa. È la verifica spostata nel runtime.
- **I criteri nascosti di Studium.** "I criteri restano nascosti" difeso da un commento HTML nel file è una
  promessa: basta aprire il file. Un comando che emette solo la parte visibile la rende vera per
  costruzione, **entro un confine**: protegge il canale agente↔utente, non il file sul disco. Va detto.
- **Il gate di questa skill.** "Non chiudere con un bloccante aperto" cede sotto "va bene così, chiudi".
  `skillauthor ready` non lo permette.

## Cosa produce questo passo

Per ogni regola di giudizio, una riga fra le **decisioni di scrittura** (vanno nel rapporto, non nella
skill):

```
Regola: <la regola>
Famiglia: estrarre | verificare | nascondere | tenere stato | nessuna
Si può garantire? sì (runtime | schema | gate) | no, perché <…>
Decisione dell'autore: spostare | tenere come promessa (col suo perché nel corpo) | rinviare
```

Se l'autore decide di spostare una regola, la skill riporta nel corpo:

1. l'**invocazione pubblica** del runtime (il comando, non i suoi moduli interni);
2. gli **schemi** di ingresso e di uscita, allegati in `references/schemas/` e citati per nome;
3. il **confine** della garanzia (cosa protegge e cosa no).

## Cosa questo passo non fa

Non scrive il runtime. Il codice segue il processo di sviluppo del progetto che possiede la capability:
requisiti, design, test. Il perché: un runtime scritto dentro la stesura di una skill nasce senza test e
senza contratto, cioè senza ciò che lo rende una garanzia.
