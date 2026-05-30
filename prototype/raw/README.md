# raw/ — Fonti esterne immutabili

Materiale sorgente che **non viene mai modificato**: paper, articoli, documentazione,
dataset, immagini. L'LLM legge da qui ma scrive solo nel [`wiki/`](../wiki/).

Sottocartelle (create su richiesta quando arriva la prima fonte):

- `articles/` — articoli, blog post, pagine web salvate
- `papers/` — paper accademici (PDF)
- `assets/` — immagini e altri asset scaricati

Quando aggiungi una fonte qui, chiedi di "ingerirla": l'LLM ne scrive un riassunto in
`wiki/sources/`, aggiorna le pagine concept/tech collegate, aggiorna
[`wiki/index.md`](../wiki/index.md) e registra l'operazione in
[`wiki/log.md`](../wiki/log.md).
