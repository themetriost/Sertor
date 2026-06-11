---
title: sertor — l'installer (pacchetto e comando)
type: tech
tags: [installer, cli, wiki, package-data, host-agnostico, produzione]
created: 2026-06-11
updated: 2026-06-11
sources: ["packages/sertor/", "specs/012-sertor-install-wiki/", "requirements/sertor-cli/installer/requirements.md"]
---

# `sertor` — l'installer

Il **veicolo d'installazione** delle capacità Sertor su un repository ospite (DA-8: `sertor` è
riservato all'install con verbo esplicito; l'esecuzione vive in [[sertor-rag-cli]] e
[[wiki-tools]]). Consegnato con la feature 012 (`specs/012-sertor-install-wiki`, PR #22,
2026-06-11). È un **pacchetto distinto** da `sertor-core` — `packages/sertor/`, modulo
`sertor_installer`, in **uv workspace** col core — perché ha ciclo di release proprio e dipende dal
core senza esserne parte (Principio I).

## Cosa fa `sertor install wiki`

Porta sull'ospite l'intero sistema-wiki con un comando, **senza mai eseguire** indicizzazioni, LLM
o rete (install ≠ run):

| Artefatto | Strategia se esiste già |
|---|---|
| Skill wiki-author (14 file) + `/wiki` + agente wiki-curator + hook di sessione | skip **file-per-file** |
| Voci hook in `.claude/settings.json` | **merge con dedup per `command`** (hook utente preservati; JSON malformato → fail-fast, mai riscritto) |
| Rituale di step nel `CLAUDE.md` | blocco a marker `SERTOR:WIKI-RITUAL`, byte-identico fuori dai marker |
| `wiki.config.toml` | generato (euristica `source_dirs` su cartelle standard, `language` default `en`, `--language`/`--source-dirs` per override); mai sovrascritto |
| Struttura `wiki/` | `structure init` del nucleo deterministico (idempotente) |

Report per artefatto (`created`/`skipped`/`merged`/`block`/`error`, anche `--json`,
schema `install.report/1`); exit 0/1/2; **fail-fast senza rollback** (il re-run completa i buchi);
idempotente per costruzione. Stub dichiarati: `install rag`, `install governance`.

## L'architettura che conta: assets come fonte

Gli artefatti non-Python viaggiano come **package-data nel wheel** (DI-5, dopo ripensamento
documentato nei requisiti §10): offline e coerenza versione-artefatti *by construction*; in
sviluppo l'install editable legge dal source tree. **Inversione di fonte (D2):**
`sertor_installer/assets/` è la **fonte canonica** e la `.claude/` del repo Sertor ne è il
**derivato** — `python -m sertor_installer.sync` propaga, e il test di guardia
(`tests/unit/test_assets_sync.py`, 17 casi) rende il drift un errore di CI. Gli assets sono
**host-agnostici** (Principio X): zero riferimenti a Sertor-il-progetto fuori dalla whitelist
(`sertor-wiki-tools`, `sertor-rag`, marker `SERTOR:WIKI-RITUAL`), verificato da test di scansione.

## Validazione (2026-06-11)

35/35 task SpecKit; root suite **221 passed + 2 xfail** (baseline intatta) + 38 test del pacchetto;
**install live su un repo ospite reale** con contenuti utente preesistenti: 19 created · 1 merged
(hook utente preservato) · 1 block · 0 errori; wiki operativo (`scan`/`validate`/`lint` sulla
config generata); re-run idempotente. Guida utente: `docs/install.md`.

## Aperto: il tema della lingua

Gli **asset testuali sono in italiano fisso** (blocco rituale, skill) anche con `language=en` nella
config generata; lo stesso vale per il seed di `structure init` ([[wiki-tools]]). Decisione utente
(2026-06-11): **da gestire** — tracciato in roadmap e nelle epiche (dote FEAT-007 / evoluzione
installer).
