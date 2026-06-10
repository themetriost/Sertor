---
title: LLM Wiki v2 (estensione agentmemory)
type: source
tags: [llm-wiki, memoria, knowledge-graph, fonte-esterna]
created: 2026-06-10
updated: 2026-06-10
sources: ["https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2"]
---

# LLM Wiki v2 (estensione agentmemory)

Gist di rohitg00 che estende il [[karpathy-llm-wiki|pattern originale di Karpathy]] con lezioni dalla
costruzione di un sistema di memoria per agenti. Conferma il nucleo («stop re-deriving, start
compiling») e propone dieci estensioni; per noi vale soprattutto come **input di design per N6 e
FEAT-004** — diverse estensioni sono cose che abbiamo già, altre sono esattamente i pezzi che ci mancano.

## Le estensioni che ci riguardano

- **Memory lifecycle** (il layer che all'originale manca): *confidence scoring* per fatto,
  **supersession esplicita** (la nuova informazione non sovrascrive in silenzio: link alla versione
  precedente, timestamp, marcatura stale), *forgetting curve* (deprioritizzazione graduale, non
  cancellazione). → È il territorio di **N6** (verità/autorità/obsolescenza, FR-012..017): la
  supersession esplicita è di fatto ciò che già pratichiamo nel log append-only (la correzione è una
  nuova voce) — N6 dovrebbe estenderla alle pagine.
- **Hybrid search per lo scaling**: oltre ~100-200 pagine, `index.md` non basta come meccanismo di
  ricerca → BM25 + vector + graph traversal fusi con **reciprocal rank fusion**, tenendo l'indice come
  catalogo leggibile. → È la ricetta di **FEAT-004** (e FEAT-005 per il grafo), detta da un terzo.
- **Typed knowledge graph**: entità e relazioni tipizzate ("uses", "depends on", "contradicts",
  "supersedes") invece di wikilink piatti; query per attraversamento. → Materiale per **FEAT-005**.
- **Automation event-driven**: hook su new-source/session-start/session-end/query/schedule. → In parte
  l'abbiamo (SessionStart/Stop, rituale di step); la differenza nostra è deliberata: D-19 ha scelto il
  trigger *manuale* contro l'automazione non presidiata.
- **«The schema is the real product»**: il documento-schema (CLAUDE.md/AGENTS.md) come artefatto più
  importante, co-evoluto e trasferibile. → Conferma forte della nostra esperienza: il nostro
  CLAUDE.md + playbook è esattamente questo.

## Le critiche nei commenti (da non perdere)

I commentatori smontano i punti deboli: il confidence scoring numerico è **falsa precisione** (mai
definito: float? chi lo calcola? — meglio una catena di link/prove); le forgetting curve sugli errori
rischiano di farli ripetere; «auto-crystallize» è magia non specificata; e soprattutto: con LLM
inaffidabili, **lo human-in-the-loop come quality gate non è un ritardo, è il controllo**. Queste
critiche pesano a nostro favore: il nostro design (lint che *segnala* e non auto-corregge, gate
eliminato D-20 ma conferma umana su reorg/contraddizioni, evidenza ancorata invece di punteggi) è
allineato alle obiezioni, non alle parti deboli del v2.

## Vedi anche

- [[karpathy-llm-wiki]] — l'originale che questo gist estende.
- [[roadmap]] — FEAT-004/005 (ibrido, grafo) e N6, i destinatari di questo materiale.
- [[deterministic-vs-judgment]] — il confine che le critiche dei commentatori confermano.
