# Quickstart — Ciclo di vita dell'installer (upgrade / uninstall)

**Feature**: `048-lifecycle-installer` (FEAT-008). Comandi PowerShell (Windows). I comandi viaggiano
col pacchetto `sertor`/`sertor-flow`; un ospite già installato deve **aggiornare il pacchetto** per
ottenerli (bootstrap del bootstrap — fuori ambito qui).

---

## 1. Vedere cosa accadrebbe (dry-run, sempre prima)

```powershell
# Cosa rimuoverebbe un uninstall del RAG, senza toccare nulla:
sertor uninstall rag --dry-run

# Cosa aggiornerebbe un upgrade del wiki:
sertor upgrade wiki --dry-run --json   # report machine-readable proiettato
```

`--dry-run`: 0 byte cambiati (SC-006); il report elenca gli esiti proiettati (`updated`/`removed`/
`skipped`).

## 2. Aggiornare un'installazione (upgrade)

```powershell
# Allinea il RAG al bundle corrente per l'assistente Claude:
sertor upgrade rag --assistant claude

# Tutto Sertor in un colpo (aggregato = capacità installate):
sertor upgrade
```

Effetto: asset standalone cambiati → sovrascritti (`updated`); blocchi a marker → contenuto dentro i
marker rinfrescato (fuori invariato); artefatti obsoleti (path Sertor-owned assente dal bundle) →
rimossi (`removed`); allineati → `skipped`. Idempotente: rieseguire su un ospite allineato → `0 updated`.

### Cambio assistente

```powershell
# Passa da copilot a copilot-cli: aggiunge gli artefatti del nuovo, rimuove quelli del vecchio non
# condivisi, lascia i comuni:
sertor upgrade rag --assistant copilot-cli
```

## 3. Rimuovere (uninstall)

```powershell
# Solo il RAG (runtime .sertor/ + blocchi/voci Sertor nei file condivisi + de-registrazione MCP):
sertor uninstall rag

# Tutto Sertor (wiki, rag, governance installati):
sertor uninstall
```

Garanzia di sicurezza: nei file condivisi (`CLAUDE.md`, `.gitignore`, `.mcp.json` con altri server,
`.claude/settings.json`) spariscono **solo** le porzioni Sertor; il resto resta byte-per-byte
invariato (SC-002).

### Proteggere / rimuovere il wiki

```powershell
# Default: il wiki/ è PRESERVATO (può contenere documentazione tua):
sertor uninstall wiki            # rimuove gli artefatti wiki ma lascia le pagine

# Rimuovere anche le pagine, con consenso esplicito (CI-safe):
sertor uninstall wiki --purge-wiki --yes    # mostra "N pagine, ~K byte" poi cancella

# Interattivo (TTY): chiede conferma y/N e mostra il conteggio prima di cancellare:
sertor uninstall wiki --purge-wiki

# Vietato (esce con codice 2):
sertor uninstall wiki --purge-wiki --dry-run
```

## 4. Governance (pacchetto separato `sertor-flow`)

```powershell
# Upgrade / uninstall della governance/SDLC (stessa semantica, stesso report):
sertor-flow upgrade
sertor-flow uninstall --assistant copilot

# Da `sertor`, governance è un PUNTATORE (rimanda a sertor-flow), nessuna dipendenza tra pacchetti:
sertor uninstall governance   # stampa il comando sertor-flow da usare
```

## 5. Output machine-readable

```powershell
sertor uninstall rag --json    # { "schema": "install.report/1", "summary": { "removed": N, ... } }
```

Schema invariato `install.report/1`, esteso coi conteggi `updated`/`removed` (vedi
`contracts/install-report-extended.md`). Exit `0` success · `1` errore di dominio · `2` usage error.

---

## 6. Verifica (per chi sviluppa la feature)

```powershell
# Suite mirata (i test vivono nei pacchetti installer; core mockato dove serve):
uv run pytest packages/sertor-install-kit packages/sertor packages/sertor-flow

# Lint:
uv run ruff check .
```

Casi di accettazione da coprire (dalla spec): rimozione byte-per-byte dei soli marker su file misto
(US2); de-registrazione MCP con client assente → fail-fast (US3); upgrade con asset+blocco+obsoleto
(US4); cambio assistente (US5); `--purge-wiki` con/senza TTY/`--yes`/`--dry-run` (US6/D4); dry-run a 0
byte (US7); aggregato (US8); parità `sertor-flow` (US9); idempotenza su ospite pulito (SC-005).
