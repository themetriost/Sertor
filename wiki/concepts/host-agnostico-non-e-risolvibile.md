---
title: Host-agnostico non è la stessa cosa di risolvibile
type: concept
tags: [asset-distribuiti, host-agnosticita, agenti, principio-x, guardie, e10, e15]
created: 2026-07-29
updated: 2026-07-29
sources: ["packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md", "packages/sertor/src/sertor_installer/assets/claude-md-block.md", "wiki/log/2026-07-29.md"]
---

# Host-agnostico non è la stessa cosa di risolvibile

Rendere un'istruzione **portabile** e renderla **utilizzabile** sono due lavori diversi, e il primo si
scambia facilmente per il secondo. Togliere da un percorso la parte specifica dell'assistente è metà
dell'opera: quel che resta — un nome di file — dice al lettore **cosa** leggere e non **dove**.

> Un payload **nominato ma non localizzabile** non è host-agnostico: è irraggiungibile su *tutti* gli
> host, in modo uniforme.

## Il caso reale (E10-FEAT-064, segnalato dal nodo *Acta*)

L'agente `wiki-curator` si fermava con `STOP — Missing Asset` su un file **presente**. La sua guardia
fail-loud funzionava esattamente come doveva: il difetto era in **cosa le avevamo detto di cercare**.

| Artefatto | Come nominava il playbook | Risolve? |
|---|---|---|
| `SKILL.md` | «`wiki-playbook.md`, **same folder**» | ✅ il lettore *è* in quella cartella |
| `agents/wiki-curator.md` | «bundled with the `wiki-author` skill (`wiki-playbook.md`)» | ❌ nessuna coordinata |
| `commands/wiki.md` | idem | ❌ |

E la riga immediatamente successiva dell'agente dichiara di sé stesso: *«You do not have the skill's
context»*. **L'istruzione riconosce che il lettore è fuori dal sistema di riferimento e, nella stessa
frase, gli dà una coordinata che presuppone di esserci dentro.** La formulazione è di *Acta*:

> una coordinata corretta, espressa nel **sistema di riferimento del lettore sbagliato**

Non è un refuso: la `SKILL.md` risolve **non per fortuna**, ma perché dice *«same folder»* — cioè offre
una coordinata utilizzabile *da chi la sta leggendo*. Dove il payload era raggiungibile la frase diceva
come raggiungerlo; dove non lo era, nominava e si fermava.

## La regola che generava il difetto

La causa non stava nell'agente: stava nella nostra **Definition of Done** per gli asset distribuiti, che
ordinava di tenere il corpo host-agnostico *«(no literal assistant paths, no slash-command invocations,
**payload referenced by name**)»*. L'ultima clausola **prescriveva il difetto**, e l'agente la rispettava.

Una regola scritta per evitare un errore (il path letterale) ne produceva un altro (la coordinata
assente), perché nominava il **rimedio** invece del **fine**.

## Come si scrive una coordinata portabile

Due forme, entrambe host-agnostiche e entrambe risolvibili:

- **Il suffisso stabile.** I container differiscono per assistente, la coda del percorso di solito no:
  ogni assistente deposita la skill in un `skills/wiki-author/`, dentro il proprio contenitore. Quindi
  `**/skills/wiki-author/wiki-playbook.md` è vero ovunque e non contiene alcun path letterale — supera
  anche la guardia di parità, che cerca la sottostringa del container.
- **L'istruzione a cercare.** Dire esplicitamente di risolvere con una ricerca, con gli strumenti che il
  lettore ha già (`Glob`/`Grep` erano fra i tool concessi all'agente fin dall'inizio: **cercare era
  possibile, non era chiesto**).

E una volta risolto il primo file, ciò che gli sta accanto non richiede una seconda ricerca: **dichiara
le parentele** («i moduli `ops/` sono fratelli del playbook»).

## Il test da applicare

Non *«ho evitato un percorso letterale?»* ma:

> **«un lettore che non è già lì riesce a risolverlo?»**

e va posto **dalla posizione di chi ha meno contesto** — che è quasi sempre un **agente delegato**, non
il flusso principale. È lì che la domanda cambia risposta: sul flusso principale la stessa frase
funzionava, perché chi legge ha più contesto e più strumenti, ed è per questo che il difetto è rimasto
invisibile per 18 giorni pur essendo **sul percorso che il nostro stesso blocco raccomanda** (*«the
`record` is delegatable to the `wiki-curator` agent»*).

## Corollario sul messaggio d'errore

Una guardia fail-loud che nomina l'asset mancante ma **non dove l'ha cercato** lascia l'ospite senza
mossa successiva: sa *cosa* manca, non *dove* dovrebbe essere. Il messaggio ora riporta anche il **glob
cercato**, così chi conosce il proprio layout può rispondere. *Fail loud* non basta: deve essere **fail
loud e azionabile**.

## Parentele

- [[esito-sull-host-vs-forma-dell-asset]] — parente stretto: là la guardia è verde e cieca perché
  osserva la **forma spedita** invece dell'**esito sull'host**; qui l'istruzione è formalmente corretta
  e inutilizzabile dal suo destinatario. In entrambi i casi ciò che manca è **il punto di vista di chi
  riceve**.
- [[identita-per-presenza-o-per-contenuto]] — l'altra famiglia di difetti «la verifica passa, la realtà
  no». Qui però nulla è idempotente: la verifica **fallisce**, ed è la verifica ad avere ragione sul
  proprio criterio e torto sul mondo.
- [[pratica-standing-vs-pratica-distribuita]] — stessa zona: ciò che vale per noi e ciò che riceve
  l'ospite non sono confrontati da nessuna guardia.
- [[dogfood-fidelity]] — perché non l'abbiamo visto: il difetto morde chi **delega** su un host che non
  è il nostro.
