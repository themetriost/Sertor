# Esempio lavorato: un agente che descrive le pull request, con `model` fissato

Agente rivisto (immaginario, costruito per l'esempio): scrive la descrizione di una pull request a partire
dal diff, delegato dal flusso principale. Intestazione:

```yaml
name: pr-describer
description: Scrive la descrizione di una pull request dal diff del branch, per conto del flusso principale.
tools: Read, Grep, Bash
model: haiku
```

Il prompt (40 righe) dice, fra l'altro:
- riga 9: «Non modifichi file e non esegui comandi che cambiano il repository: leggi soltanto»;
- riga 11: «Ricava le modifiche con `git diff <destinazione>...<branch>` e `git log --oneline`»;
- righe 14–16: il brief contiene il branch e il ramo di destinazione; «se manca il ramo di destinazione,
  usa `main`»;
- righe 22–23: «Chiudi la descrizione con la riga `Scritta da <il tuo modello>`»;
- righe 36–40: il rapporto è la descrizione stessa, seguita da «nient'altro».

È distribuito su Claude Code e Codex.

## 1. Fatti meccanici

```text
skillauthor agent-lint pr-describer.md --targets claude-code,codex --json
```

`tools_declared: true` (`Read, Grep, Bash`), `model_declared: true` (`haiku`),
`shell_tools: {"declared": ["Bash"], "uncovered": ["windows"]}`. Parità: su Codex `tools` e `model`
risultano `dropped` (due finding P, avvisi). Un finding T bloccante (`claude-code:tools`): la sola shell
dichiarata non esiste su Windows senza bash. Nessun F, H, R. Exit 1. Da soli, i fatti non sono difetti; il
finding T va verificato nel prompt (passo 2).

## 2. Lettura per dimensioni

- **Intestazione.**
  - `model: haiku` fissa il modello, e le righe 22–23 fanno dipendere la firma dal modello: la riga sarà
    sempre «Scritta da» quel modello, qualunque cosa chieda il brief. Fatto con una dipendenza → **finding**.
  - `tools` è ristretto, ma contiene `Bash`: la shell scrive file e fa versioning. Il confine della riga 9
    («leggi soltanto») resta una **promessa**, non una costruzione. Il `tools` ristretto non lo rende vero.
    Il confine però è dichiarato, e chi delega lo conosce → **finding**, miglioria. La shell serve per
    `git` (riga 11), quindi non si può togliere: la costruzione qui non è disponibile.
  - Gli strumenti bastano? L'unica azione oltre alla lettura è eseguire `git` (riga 11), e la permette
    solo `Bash`: su Claude Code in Windows senza bash l'agente non ha shell e non può ricavare il diff. È
    il finding T del runtime, confermato dal prompt → **finding** bloccante. Su Codex `tools` non arriva,
    quindi lì la shell c'è.
- **Brief.** Il ramo di destinazione mancante ha un default (`main`, righe 14–16), ma nessun obbligo di
  dichiararlo. Un default sbagliato produce una descrizione contro il ramo sbagliato senza che chi delega lo
  veda → **finding** (anche dimensione 4).
- **Rapporto.** Righe 36–40: il rapporto è solo la descrizione. Non c'è posto per gli scostamenti dal brief
  né per i default usati → **finding**, unito al precedente.
- **Autorità.** Il ramo di destinazione è una decisione di chi delega: il default è ammesso solo se
  dichiarato e restituito come domanda (vedi sopra).
- **Parità.** Su Codex `tools` e `model` non arrivano: lì l'agente ha tutti gli strumenti e il modello
  dell'ospite. Il confine «leggi soltanto» è già scritto nel prompt (riga 9), quindi sopravvive come
  promessa, e su Codex la firma cambia modello. Nessun nuovo bloccante, ma va detto.

## 3. Rapporto

```text
Review dell'agente pr-describer (destinazioni: Claude Code, Codex; parità: kaelen 0.16.1 placement)

Bloccanti
B1 [intestazione, autorità] La firma dipende dal model fissato e un brief non la può cambiare.
   Prova: model: haiku; righe 22–23 «Scritta da <il tuo modello>».
   Effetto: un brief che chiede un'altra attribuzione viene disatteso in silenzio; su Codex, dove model
   non arriva, la firma cambia senza che nessuno l'abbia deciso.
   Proposta (scelta dell'autore): o «se il brief indica la firma, usa quella» (prevale il brief), o «la
   firma è sempre il modello che esegue; se il brief ne chiede un'altra, dichiaralo» (prevale l'agente,
   ma lo dichiara).

B2 [brief, rapporto, autorità] Il default del ramo di destinazione non è dichiarato, e il rapporto non ha
   posto per dichiararlo.
   Prova: righe 14–16 «usa main»; righe 36–40 «nient'altro».
   Effetto: con un brief incompleto la descrizione può riferirsi al ramo sbagliato, e chi delega non lo sa.
   Proposta: dopo la descrizione, una sezione «Scostamenti e default usati»; il ramo assunto va lì e fra le
   domande.

B3 [intestazione] Su Windows senza bash l'agente resta senza shell e non può ricavare il diff.
   Prova: tools: Read, Grep, Bash (runtime T, shell_tools.uncovered: windows); riga 11 «git diff …».
   Effetto: delegato su una macchina Windows, l'agente fallisce a metà o scrive la descrizione senza diff,
   e chi delega lo scopre dal risultato.
   Proposta: tools: Read, Grep, Bash, PowerShell; i comandi della riga 11 sono gli stessi nelle due shell.

Migliorie
M1 [intestazione] «Leggi soltanto» è una promessa: la shell scavalca il tools ristretto.
   Prova: tools: Read, Grep, Bash; riga 9.
   Effetto: un brief che chiede «e già che ci sei, fai il push» trova l'agente capace di farlo, e solo la
   promessa della riga 9 lo trattiene.
   Proposta: la shell serve per git (riga 11), quindi non si toglie: scrivere nel prompt il perché del
   confine e cosa fare se il brief lo contraddice.

Note
- Parità: su Codex tools e model si perdono (P); il confine «leggi soltanto» sopravvive perché è anche nel
  prompt.
- Prova a freddo: non chiesta.
```

Registro (trascritto dopo il rapporto, conforme a `references/schemas/review.schema.json`; i campi
`dimension`, `evidence` e `proposal` sono aggiunti dalla review e lo schema li ammette; più dimensioni si
scrivono separate da virgola):

```json
{
  "skill_name": "pr-describer",
  "round": 1,
  "findings": [
    {"id": "B1", "severity": "blocking", "status": "open",
     "summary": "La firma dipende dal model fissato e il brief non la può cambiare",
     "dimension": "intestazione, autorità", "evidence": "model: haiku; pr-describer.md:22-23",
     "proposal": "Dire se prevale il brief o l'agente, e dichiarare lo scostamento"},
    {"id": "B2", "severity": "blocking", "status": "open",
     "summary": "Default del ramo di destinazione non dichiarato, nessun posto nel rapporto",
     "dimension": "brief, rapporto, autorità", "evidence": "pr-describer.md:14-16; pr-describer.md:36-40",
     "proposal": "Sezione 'Scostamenti e default usati' e ramo assunto fra le domande"},
    {"id": "B3", "severity": "blocking", "status": "open",
     "summary": "Su Windows senza bash l'agente resta senza shell e non può ricavare il diff",
     "dimension": "intestazione", "evidence": "tools: Read, Grep, Bash (agent-lint T); pr-describer.md:11",
     "proposal": "Aggiungere PowerShell a tools"},
    {"id": "M1", "severity": "improvement", "status": "open",
     "summary": "Il confine 'leggi soltanto' è una promessa: la shell scavalca il tools ristretto",
     "dimension": "intestazione", "evidence": "tools: Read, Grep, Bash; pr-describer.md:9",
     "proposal": "Scrivere il perché del confine e cosa fare se il brief lo contraddice"}
  ]
}
```

## Cosa non è stato segnalato, e perché

- `model: haiku` **come scelta di costo**: per un compito di scrittura breve è legittimo. Il finding è sulla
  firma che ne dipende, non sul modello.
- I due finding P di Codex non diventano bloccanti: il confine che `tools` esprimeva è ripetuto nel prompt.
- Mancanza di strumenti di scrittura (`Write`, `Edit`): l'agente non deve scrivere file, il rapporto è la
  descrizione stessa. Nessuna azione richiesta resta senza strumento, a parte la shell di B3.
