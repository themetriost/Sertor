# Collaudo di una correzione

Il collaudo misura se l'agente corretto si comporta meglio di quello di prima, sui brief dove il finding diceva
che sbagliava. Il protocollo è quello della skill `skill-authoring`, passo «Collaudo»: workspace, esecuzioni in
sottoagenti nuovi, valutazione alla cieca, verdetto. Qui c'è solo come si applica a un agente.

## Le due configurazioni

Il runtime legge il workspace con due configurazioni dai nomi fissi. Per una correzione si usano così:

| Cartella | Cosa gira lì |
|---|---|
| `with_skill` | l'agente **corretto** |
| `without_skill` | l'agente **di prima**, cioè la copia della sorgente presa prima di scrivere |

Ogni esecutore riceve la definizione dell'agente (intestazione e prompt) come proprio ruolo, più il brief del
caso. Nessuno dei due riceve questa skill: si confrontano due agenti, non una skill.

**Confine:** se l'esecutore riceve la definizione come testo, `tools` e `model` non valgono, perché a imporli è
l'assistente che avvia l'agente, non il testo. Il collaudo misura il prompt. I cambi d'intestazione si provano con
`agent-diff` e `agent-lint`, non con un brief.

## I casi

Per ogni finding che la correzione chiude servono due brief:
- **reale:** come lo scriverebbe chi delega davvero, e porta all'azione che il finding contesta. Per esempio, per
  un finding sulla firma dei commit, un brief che chiede di committare;
- **povero:** omette proprio ciò che il finding contesta. Per esempio non dice quale firma usare, o non autorizza
  un'operazione irreversibile.

Ogni caso ha almeno un'asserzione di **merito** (il risultato è giusto per chi delega) e asserzioni di
**protocollo** (l'agente si è fermato, ha chiesto, ha dichiarato lo scostamento). Per ogni brief registra se
l'agente **si è fermato, ha chiesto o ha deciso da solo**.

`evals.json` e i file dei casi stanno nel workspace, **fuori** dalla cartella dell'agente e fuori da questa skill.

## Costo e consenso

Il costo è: casi × 2 configurazioni × giri, in esecuzioni, più altrettante valutazioni. Lo calcola
`skillauthor cost <workspace> --evals <workspace>/evals.json`. Dichiaralo all'autore e aspetta il sì prima di lanciare.

## Verdetto

```text
skillauthor verdict <workspace> --evals <evals.json> --skill <sorgente-corretta> --json
```

Con un file in `--skill`, il verdetto registra l'impronta dell'agente corretto. Annota `skillauthor digest
<sorgente>` **prima** delle esecuzioni e controlla che coincida: se no, qualcosa ha toccato l'agente durante il
collaudo.

- **`validated`:** la correzione separa sul merito.
- **`protocol-only` o `no-separation`:** dillo com'è. Spesso vuol dire che l'agente di prima, su quel brief, si
  comportava già bene, o che l'asserzione era debole. Decide l'autore.

## Il confronto con un agente capace

Quando serve sapere se la correzione vale più di un agente generico (per esempio per il primo caso di una
capability), si aggiunge un **secondo workspace** con lo stesso layout:
- `with_skill`: l'agente corretto;
- `without_skill`: un agente capace che riceve lo stesso brief e nessuna definizione.

Si riporta **a parte**: risponde a un'altra domanda.

## Se l'ospite non avvia sottoagenti

Il collaudo è **non eseguito**. Nel rapporto metti i casi pronti, il costo e il motivo. Non eseguire i brief
nella stessa conversazione per poi chiamarlo collaudo: senza esecutori nuovi e un valutatore che non ha scritto la
correzione non misura niente. Senza verdetto il gate risponde `verdict-missing`, e l'agente non è pronto.
