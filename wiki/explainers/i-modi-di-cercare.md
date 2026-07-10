---
title: I modi di cercare (in parole semplici)
type: explainer
tags: [non-tecnici, motori, ibrido, grafo, agentico, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/concepts/vector-retrieval.md", "wiki/concepts/hybrid-retrieval.md", "wiki/concepts/code-graph.md", "wiki/concepts/retrieval-vs-graph.md"]
---

# I modi di cercare

Cercare "per significato" si può fare in modi via via più furbi. Sertor ne ha quattro, e li puoi
combinare o scegliere a seconda di cosa ti serve.

## 1. La ricerca per significato (la base)

Trova i pezzi il cui *argomento* somiglia alla domanda. Ottima per domande concettuali («come funziona
il login?»). Punto debole: se cerchi un **nome preciso** (una funzione che si chiama esattamente
`reset_password`), il "somiglia come argomento" a volte la manca.

## 2. La ricerca mista (oggi la predefinita)

Mette insieme due bibliotecari: uno cerca **per significato** (punto 1) e uno cerca **per parola
esatta**, e poi fondono i risultati. Così prendi il meglio dei due: i concetti *e* i nomi precisi.
È il motivo per cui oggi Sertor trova bene anche i simboli con nome esatto.

*L'immagine:* due ricercatori, uno che capisce gli argomenti e uno che ricorda le parole esatte, che
si confrontano e ti danno la lista combinata.

## 3. La mappa delle connessioni (il grafo del codice)

Oltre a *cosa* dice ogni pezzo, Sertor sa anche **come i pezzi si collegano**: questa funzione *chiama*
quell'altra, questo documento *parla di* quel componente. È una **mappa delle relazioni**. Serve a
domande tipo «chi usa questa funzione?» o «dove è definita?» — risposte che la sola somiglianza di
argomento non dà.

*L'immagine:* non solo le schede dei libri, ma anche il filo che collega chi cita chi.

## 4. La ricerca "ragionata" (agentica)

Qui entra in gioco l'assistente AI: davanti a una domanda complessa **non fa una sola ricerca**, ma
ragiona a passi — cerca, legge, si accorge che gli manca un pezzo, cerca ancora, e infine mette
insieme la risposta citando le fonti. Sertor gli mette a disposizione gli strumenti (i punti 1-3);
l'AI li orchestra.

*L'immagine:* un investigatore che segue gli indizi uno dopo l'altro invece di accontentarsi della
prima cosa che trova.

## Quando usare quale: «prima scopri, poi naviga»

I due strumenti più usati — la **ricerca mista** (punto 2) e la **mappa delle connessioni** (punto 3)
— non sono in concorrenza: si usano **in sequenza**.

- **Quando NON sai dove sta una cosa** → usa la **ricerca mista**. È brava a trovare per argomento:
  «dov'è la parte che gestisce i nuovi tentativi?» ti porta al pezzo giusto anche se non ne conosci il
  nome. È **scoprire**.
- **Quando GIÀ conosci il nome di qualcosa** → usa la **mappa delle connessioni**. «Chi usa questa
  funzione? cosa si rompe se la cambio? dov'è definita?» sono domande di *relazione*, e la mappa dà
  risposte **esatte**. È **navigare**.

*L'immagine:* prima chiedi al bibliotecario «dove trovo i libri su questo tema?» (scopri), poi, preso
il libro giusto, segui le note a piè di pagina per vedere chi cita chi (navighi). Usare la mappa
quando non sai ancora da quale libro partire non serve; cercare «per tema» quando ti serve sapere «chi
cita esattamente questo» non basta.

## In sintesi

| Modo | Per cosa è bravo | Quando |
|---|---|---|
| Per significato | Domande concettuali | — |
| Mista (predefinita) | Concetti **e** nomi esatti | **scoprire** (non sai dove sta) |
| Mappa delle connessioni | «Chi chiama cosa», «dov'è definito» | **navigare** (conosci già il nome) |
| Ragionata (AI) | Domande complesse, a più passi | l'AI orchestra gli altri tre |

---

*Dettaglio tecnico:* [[vector-retrieval]] · [[hybrid-retrieval]] · [[code-graph]]; la guida di scelta
«scopri → naviga» in [[retrieval-vs-graph]]; la modalità ragionata nasce dalla coppia
[[mcp-server|assistente + strumenti]].
