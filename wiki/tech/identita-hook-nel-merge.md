---
title: Identità di un hook nel merge (per script, non per stringa)
type: tech
tags: [installer, hook, settings-merge, upgrade, sertor-install-kit, e10, feat-031, feat-032]
created: 2026-07-17
updated: 2026-07-17
sources: ["packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py", "packages/sertor-install-kit/tests/unit/test_settings_merge_identity.py", "requirements/debito-tecnico/epic.md", "wiki/log/2026-07-16.md", "wiki/log/2026-07-17.md"]
---

# Identità di un hook nel merge (per script, non per stringa)

Quando `sertor install`/`upgrade` cabla un hook, deve rispondere a una domanda che sembra banale:
**«questo hook c'è già?»**. La risposta dipende da *cosa consideriamo l'identità* dell'hook — ed è la
scelta che ha deciso se un fix arrivava o no agli ospiti. Meccanismo in
[`settings_merge.py`](../../packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py)
(pacchetto [[sertor-install-kit]]); i verbi che lo usano stanno in [[installer-lifecycle]].

## Il difetto: la stringa del comando come identità

Il merge deduplicava per **stringa del comando esatta**. Ma Sertor **ri-cabla lo stesso hook nel
tempo** — e l'ha fatto tre volte:

| Transizione | Cosa cambia nel comando | Feature |
|---|---|---|
| PowerShell → Python portabile | `pwsh -File …x.ps1` → `uv run … python …x.py` | A-09 |
| path relativo → ancorato | `…/.claude/hooks/x.py` → `"${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"` | FEAT-031 |
| aggiunta di `cwd` (Copilot) | il `command` **non cambia**, cambia una chiave sorella | FEAT-031 |

La stringa del comando è dunque un **dettaglio di resa mutabile**, non un'identità. Usarla come chiave
faceva sembrare **nuovo** ogni ri-cablaggio, con due esiti opposti e ugualmente rotti:

- **Claude** — la voce vecchia non era riconosciuta come «la stessa» → **sopravviveva**, e la nuova
  veniva **appesa**: lo stesso hook cablato **due volte**, con la copia vecchia **ancora attiva**. Su
  `PreToolUse` significava che l'hook rotto continuava a bloccare `Bash`/`Write`/`Edit`. Il fix
  FEAT-031 arrivava alle **install nuove**, non a chi **aggiornava**.
- **Copilot** — cambiava solo la chiave sorella `cwd`, il `command` restava identico → la dedup
  considerava la voce «già presente» e **scartava la nuova**: il fix **non atterrava mai**, *in
  silenzio*.

Era una **classe di bug, non un'istanza**: la primitiva di rimedio
`remove_hook_entries_by_command_substring` esisteva già (scritta per A-09) ma copriva solo i basename
`.ps1` ed era chiamata solo in `_apply_rag_upgrade` — ogni transizione andava rincorsa a mano, e la
successiva ripartiva da zero.

## Il fix: l'identità è lo *stem* dello script

L'identità di un hook è lo **stem dello script** che esegue — `rag-freshness`, da `rag-freshness.py`
*o* `rag-freshness.ps1`. È ciò che **sopravvive a ogni ri-cablaggio**, mentre tutto il resto (path,
interprete, flag, `cwd`) è resa. Un solo cambio chiude **tutte e tre** le transizioni insieme, invece
di inseguirle una per una:

```python
_SCRIPT_RE = re.compile(r"([\w][\w.-]*)\.(?:py|ps1)\b")   # lo stem = l'identità
```

## I due contratti, ora espliciti

Il fix ha reso esplicito un confine che prima era implicito e violato:

- **`merge_settings(..., replace_stale=False)` = `install`** — idempotente e **non distruttivo**: non
  rimuove nulla (è il contratto che *definisce* `install`) **e ora non duplica più**. La forma stantia
  resta, ma viene **nominata nel report**, indicando all'ospite di eseguire `upgrade`. Prima **taceva**:
  è l'applicazione del [[constitution|Principio XII]] «Fail Loud» a un path che falliva muto.
- **`merge_settings(..., replace_stale=True)` = `upgrade`** — sostituisce **in place** e **collassa**
  tutte le rese dello stesso hook in una: *un hook = un wiring per evento*. Le voci **dell'utente** non
  vengono mai toccate (solo il wiring di proprietà di Sertor).

**Deliberatamente NON** si è fatto delegare `install` → `upgrade`: romperebbe la non-distruttività che
definisce `install` — un utente che installa non si aspetta rimozioni. I due verbi restano distinti;
è il report a fare da ponte.

## Perché i test non l'avevano colto

Le guardie verificavano che l'**asset** dichiarasse il wiring giusto, non l'**esito su un host che
aggiorna**: il buco stava esattamente fra le due cose. È la lezione distillata a parte in
[[esito-sull-host-vs-forma-dell-asset]] — le 10 nuove guardie di
`test_settings_merge_identity.py` asseriscono l'esito d'upgrade, non la forma.

## Verifica indipendente

Il bug è stato **confermato dal nodo Noetix** prima di essere corretto: il dogfood era un **teste
contaminato** (il bug era stato prodotto sullo stesso nodo che avrebbe scritto il fix), quindi la
conferma è stata chiesta a un ospite indipendente che aggiornava da HEAD. Vedi [[dogfood-fidelity]]
per perché il dogfood da solo non basta come prova.

## Riferimenti

- Consegna: E10-FEAT-032, merge `ddbfb27`/PR #192 (2026-07-17) — completa **FEAT-031** (hook wiring ancorato, merge `e3c2a97`/PR #190).
- Meccanismo: [[sertor-install-kit]] · verbi: [[installer-lifecycle]] · lezione: [[esito-sull-host-vs-forma-dell-asset]].
