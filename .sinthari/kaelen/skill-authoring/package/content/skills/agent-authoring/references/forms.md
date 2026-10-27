# Le forme di un agente

Uno stesso agente può essere collocato in forme diverse, una per assistente:

| Forma | Assistente | Intestazione | Prompt |
|---|---|---|---|
| `<nome>.md` | Claude Code | fra `---`, con `name`, `description`, spesso `tools` e `model` | il corpo |
| `<nome>.agent.md` | GitHub Copilot | fra `---`; `tools` e `model` hanno un altro vocabolario o mancano | il corpo |
| `<nome>.toml` | Codex | `name`, `description`; niente `tools` né `model` | il campo `developer_instructions` |

La tabella segue le regole di collocazione di Kaelen 0.16.1, la stessa fonte che il runtime dichiara nell'esito.

## Sorgente unica

Si cerca in quest'ordine:
1. **la dichiarazione d'installazione del produttore:** di solito un `*.declaration.toml`, con un item di tipo
   agente e il percorso della sua sorgente;
2. **l'autore,** se lo indica;
3. **nessuna:** le forme sono scritte a parte, una per una.

## Se c'è una sorgente unica

- **Correggi solo la sorgente.** Le forme derivate le rigenera il motore che le ha prodotte, cioè l'aggiornamento
  della capability che le installa, su richiesta dell'autore. Correggerle a mano le farebbe divergere al
  prossimo aggiornamento, che le riscriverebbe dalla sorgente.
- **Nel rapporto** elenca ogni forma derivata come `to-regenerate`, e dì chi la rigenera.
- **Forma derivata o copia di sviluppo?** Una forma elencata nel registro di un'installazione (in una cartella
  che finisce in `kaelen/<capability>/`) è derivata: non la tocchi. Una copia identica alla sorgente, nella stessa
  forma, che nessun registro elenca, è una copia di sviluppo: la ricopi dalla sorgente e lo dichiari nel rapporto.
- **La rigenerazione non la fai tu.** Con forme derivate ti fermi, consegni il rapporto con le forme
  `to-regenerate`, e riprendi da `agent-forms` quando l'autore dice che sono rigenerate.
- **Dopo la rigenerazione** verifica:

  ```text
  skillauthor agent-forms <sorgente> <forma>... --json
  ```

  | Stato | Significato | Cosa fai |
  |---|---|---|
  | `in-sync` | campi e prompt coincidono | niente |
  | `declared-losses-only` | mancano solo campi che quell'assistente non rappresenta | scrivi la perdita nel rapporto |
  | `unverified` | un campo che quell'assistente rappresenta in modo diverso c'è, ma il runtime non lo sa confrontare (oggi `tools` e `model` su Copilot). Il dettaglio riporta i due valori | leggili tu e scrivi nel rapporto che sono verificati a occhio |
  | `diverges` | un campo rappresentato manca o è diverso (`missing`, `different`), oppure il prompt non coincide (`prompt-differs`) | la forma non è allineata: fai rigenerare, non correggere a mano |

**Leggi sempre ogni voce di `differences`:** lo stato riassume la forma intera. Una `declared-loss` di un campo
che quell'assistente rappresenta in modo diverso (oggi `tools` o `model` su Copilot) non è una perdita
inevitabile: una forma Copilot senza `tools` ha tutti gli strumenti, ed è da rigenerare. Il campo `in_sync` in
testa all'esito vale `true` anche con forme `unverified`: non bastarlo da solo.

**Confine:** `in-sync` vuol dire che coincidono i campi che il runtime sa confrontare e il prompt. Su Copilot
`tools` e `model` non li confronta: li segnala come `unverified` quando ci sono. Non dichiarare la parità di quei
campi sulla base del solo `agent-forms`.

Il gate rifà lo stesso confronto con `--form`. Passagli **tutte** le forme che il rapporto elenca: il gate
verifica solo quelle che riceve, e non le cerca da sé. Le differenze `unverified` non bloccano il gate: le trovi
fra le sue `notes`.

## Se l'agente è per un solo assistente

Non c'è niente da confrontare: scrivi «parità non applicabile» nel rapporto.

## Se non c'è una sorgente unica

Applica ogni correzione a ogni forma, oppure dichiara quali forme hai lasciato invariate e perché. Poi confronta
le forme fra loro, prendendone una come riferimento, con `agent-forms`.

## Un limite che una forma non rappresenta

Esempio: la correzione restringe `tools`, ma Codex non legge `tools`. Su Codex il limite non vale.

1. **Nel rapporto** nomina il campo perso e l'assistente.
2. **Porta il limite nel prompt dove puoi**, in parole: per esempio «non eseguire comandi che modificano il
   repository». È una promessa, non una garanzia: dillo.
3. **Non dichiarare la parità.** Una forma che perde un limite non è equivalente alle altre, anche se il runtime
   la dà `declared-losses-only`.
