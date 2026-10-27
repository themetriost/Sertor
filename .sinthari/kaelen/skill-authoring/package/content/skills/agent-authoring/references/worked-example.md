# Esempio lavorato: correggere `ticket-triager`

Un agente inventato, per mostrare un ciclo completo. Non è un agente reale di nessun progetto.

## La situazione

La sorgente è `agents/ticket-triager.md`, nominata dalla dichiarazione d'installazione del progetto. L'ospite
tiene due forme derivate: `.github/agents/ticket-triager.agent.md` per Copilot e `.codex/agents/ticket-triager.toml`
per Codex.

```markdown
---
name: ticket-triager
description: Smista i ticket nuovi seguendo la skill triage-rules.
tools: Bash, Read
model: haiku
---

Leggi i ticket con `gh issue list`. Applica la skill `triage-rules`.
Etichetta ogni ticket. Non chiudere mai un ticket.
```

La review di `agent-review` (`review-1.json`) ha tre finding. Chi l'aveva chiesta aveva annotato prima
l'impronta dell'agente nel registro (`subject_digest: sha256:aa11…`), perché `agent-review` non la scrive:
- **B1, bloccante:** dichiara solo `Bash`. Su Windows senza bash l'agente resta senza shell, e il prompt la usa;
- **B2, bloccante:** il prompt dice «non chiudere mai un ticket», mentre `triage-rules` chiede di chiudere i
  duplicati;
- **M1, miglioria:** il rapporto non dichiara gli scostamenti dal brief.

## 1. Letture e review attuale

`skillauthor digest agents/ticket-triager.md --json` dà `sha256:bb22…`, diverso da `aa11…`: qualcuno ha toccato
l'agente dopo la review. L'impronta dice solo che è cambiato, non cosa. L'ospite ha un versioning: nella cronologia
del file c'è la versione con impronta `aa11…`, e il confronto mostra una sola riga cambiata, la description. Lo si
mostra all'autore:

> La review è stata fatta su una versione precedente. Da allora, secondo la cronologia, è cambiata solo la
> description, che nessun finding tocca. Confermi che B1, B2 e M1 valgono ancora, o vuoi una review nuova?

Senza cronologia si sarebbe detto che non si sa cosa è cambiato.

L'autore conferma: «sì, valgono, la description non c'entra». Le sue parole vanno nel rapporto. Senza conferma ci
si sarebbe fermati qui.

## 2. Proposte

| # | Finding | Tipo | Prima | Dopo |
|---|---|---|---|---|
| P1 | B1 | header | `tools: Bash, Read` | `tools: Bash, PowerShell, Read` |
| P2 | B2 | prompt | «Non chiudere mai un ticket.» | (dipende dalla scelta dell'autore, sotto) |
| P3 | M1 | prompt | (assente) | «Nel rapporto dichiara ogni cosa che non hai fatto o hai fatto diversamente dal brief, e perché.» |

**P1, cambio di potere, approvazione a parte:**
- **prima:** shell solo dove c'è bash;
- **dopo:** shell anche su Windows tramite PowerShell;
- **che cosa ne segue:** nessuna azione nuova, ma `gh issue list` diventa eseguibile su ogni sistema;
- **perdite:** su Codex `tools` non vale, quindi non c'è perdita nuova. Su Copilot il vocabolario è diverso, e lo
  si dichiara.

**P2, contraddizione con la skill delegata.** Le due righe:
- `agents/ticket-triager.md:8`: «Non chiudere mai un ticket.»;
- `triage-rules/SKILL.md:41`: «Chiudi i duplicati con un rimando all'originale.».

Le opzioni:
1. il prompt permette di chiudere i soli duplicati, con il rimando;
2. la skill smette di chiudere i duplicati: costa il ricollaudo di `triage-rules`;
3. l'agente etichetta i duplicati, e la chiusura la fa chi lo ha delegato.

La raccomandazione è la (1): rispetta l'intento della skill e tiene il divieto per tutto il resto. La scelta resta
all'autore, che sceglie la (3): «preferisco che le chiusure le faccia un umano».

Le approvazioni sono due, separate. Prima il cambio di poteri: l'autore approva P1, «sì, aggiungi
PowerShell». Poi le modifiche al prompt: approva P2 nella versione (3) e P3.

## 3. Scrittura

Prima di scrivere si copia la sorgente nel workspace del collaudo (`before/ticket-triager.md`). Poi si scrivono le
tre modifiche, e:

```text
skillauthor agent-diff before/ticket-triager.md agents/ticket-triager.md --json
```

L'esito: `tools: {"added": ["PowerShell"], "removed": []}`, nessun altro campo cambiato, prompt `+3 −1`. Si
riporta così com'è. Poi `agent-lint`, con le destinazioni e la cartella delle skill, sulla copia di prima e
sulla sorgente:

```text
skillauthor agent-lint agents/ticket-triager.md --targets claude-code,github-copilot,codex --skills-dir skills --json
```

Prima c'era un bloccante T (era B1); dopo non c'è più, e non ne compaiono di nuovi.

## 4. Forme

Le due forme derivate si elencano come `to-regenerate`. Le rigenera l'aggiornamento della capability, su richiesta
dell'autore. Qui il ciclo si ferma: il rapporto consegna le due forme da rigenerare. Si riprende quando l'autore
dice che sono rigenerate:

```text
skillauthor agent-forms agents/ticket-triager.md .github/agents/ticket-triager.agent.md .codex/agents/ticket-triager.toml
```

- Copilot: `unverified`. La forma rigenerata porta `tools`, che su Copilot ha un altro vocabolario e il runtime
  non confronta: il dettaglio mostra i due valori, e li si controlla leggendo la forma. Nel rapporto si scrive
  «tools su Copilot verificato a occhio».
- Codex: `declared-losses-only`, perché `tools` e `model` non sono rappresentati. Il limite sulla shell non vale
  su Codex: lo si scrive nel rapporto.

## 5. Collaudo

Due finding con un comportamento da misurare (B1 dipende dal sistema operativo, quindi si misura con
`agent-lint`, non con un brief):
- **B2, brief reale:** «smista i ticket di oggi», con un duplicato fra i ticket. Asserzione di merito: il
  duplicato è etichettato e non chiuso. Asserzione di protocollo: l'agente lo dice nel rapporto;
- **M1, brief povero:** «smista i ticket», senza dire cosa fare con quelli senza area. Asserzione di protocollo:
  il rapporto dichiara la scelta fatta.

Il costo è 2 casi × 2 configurazioni = 4 esecuzioni + 4 valutazioni, più 1 esecuzione per la review
indipendente. L'autore approva. L'agente di prima va in
`without_skill`, quello corretto in `with_skill`. Esito: `validated`, perché l'agente di prima chiudeva il
duplicato e quello corretto no.

## 6. Review e gate

Si calcola `digest` della sorgente corretta e si avvia `agent-review` in un sottoagente nuovo, registrando
`subject_digest` in `review-2.json`. Nessun bloccante. Poi:

```text
skillauthor ready agents/ticket-triager.md --review review-2.json --verdict verdict.json --form .github/agents/ticket-triager.agent.md --form .codex/agents/ticket-triager.toml
```

Esito: `ready`.

## Il rapporto, in breve

1. **Domande aperte:** nessuna.
2. **Gate:** `ready`.
3. **Collaudo:** `validated`, separa l'asserzione di merito su B2.
4. **Finding:** B1, B2 e M1 risolti.
5. **Modifiche:** P1, P2 (opzione 3) e P3, tutte approvate, con le parole dell'autore, più l'esito di
   `agent-diff`.
6. **Forme:** Copilot rigenerata, `unverified` (tools controllato a occhio); Codex rigenerata,
   `declared-losses-only`, e il limite sulla shell non vale su Codex.
7. **File:** `agents/ticket-triager.md`.
8. **Costo:** 4 esecuzioni, 4 valutazioni, 1 review.
9. **Scostamenti:** la review era della versione precedente, e l'autore ha confermato che i finding valevano
   ancora (parole citate).
