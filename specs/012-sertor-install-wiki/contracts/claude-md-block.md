# Contratto — Blocco a marker nel `CLAUDE.md` (FEAT-012)

**Branch**: `012-sertor-install-wiki` | **Spec**: [`../spec.md`](../spec.md) | **Data**: 2026-06-11

Formato e semantica del blocco step-ritual che `sertor install wiki` inserisce nel `CLAUDE.md`
dell'ospite (FR-014 / REQ-122, decisione D4). Il **contenuto** del blocco vive negli assets
(`sertor_installer/assets/claude-md-block.md`) ed è **host-agnostico** (Principio X / SC-004).

---

## Formato dei marker

```markdown
<!-- SERTOR:WIKI-RITUAL START -->
## Rituale di step (LLM Wiki)

…sezione step-ritual host-agnostica…
<!-- SERTOR:WIKI-RITUAL END -->
```

- Marker su **riga propria**, commento Markdown/HTML (coerente con `<!-- SPECKIT START/END -->` e
  `<!-- EXEC:START/END -->` già usati nel repo).
- Prefisso `SERTOR:` = namespace di proprietà (qualifica chi possiede il blocco; è il **nome del
  prodotto**, non un riferimento *host-specifico* → non viola X).
- Tutto **dentro** i marker è di proprietà dell'installer; tutto **fuori** è dell'utente e
  intoccabile.

## Algoritmo di scrittura (idempotente, non-distruttivo — D4)

| Stato `CLAUDE.md` | Azione | Outcome |
|-------------------|--------|---------|
| assente | crea il file col solo blocco (marker + contenuto) | `BLOCK` (created) |
| presente, marker **assenti** | appendi il blocco in coda (preceduto da riga vuota); resto intoccato | `BLOCK` |
| presente, marker **presenti** | **non toccare nulla** (anche se l'utente ha modificato dentro i marker) | `SKIPPED` |

**Idempotenza (SC-003):** il re-run trova i marker → skip → nessuna duplicazione.
**Non-distruttività (SC-002):** nei casi "presente", il contenuto **fuori** dai marker resta
byte-per-byte identico.

> **Upgrade (fuori ambito).** Riscrivere il *contenuto dentro* i marker preservando l'esterno è il
> comportamento di un futuro `--upgrade` (spec Assumptions): il formato marker lo abilita già. FR-014
> richiede solo «non duplicare al re-run» → lo skip basta.

## Contenuto del blocco (host-agnostico)

La sezione step-ritual bundlata MUST riferire solo nomi **standard/di prodotto**, mai percorsi o
domini di Sertor:
- delega al ruolo **`wiki-curator`** (agente installato) e al comando **`/wiki`**;
- la configurazione vive in **`wiki.config.toml`** (l'ospite si configura);
- i path citati sono convenzioni Claude Code (`.claude/…`) o nomi-file generici (`wiki/`,
  `index.md`) — risolti via config, non assunti.

**Verifica (SC-004):** scansione del blocco installato → zero occorrenze di `Sertor`/`prototype`/
percorsi del repo Sertor.
