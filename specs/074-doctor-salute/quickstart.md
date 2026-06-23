# Quickstart — `sertor-rag doctor` (E12-FEAT-001)

> Tutti gli esempi sono **PowerShell** (Windows). `doctor` è sola lettura: non scrive mai su config o
> indice.

## 1. «Ha funzionato?» in un comando

```powershell
sertor-rag doctor
```

Riporta le quattro aree (config · provider · indice · MCP) con esito pass/warn/fail. Exit 0 se nessun
check critico fallisce; exit 1 se env è incompleto o l'indice è assente.

## 2. Esito machine-readable (skill / CI)

```powershell
sertor-rag doctor --json
```

Emette `doctor.report/1` (schema stabile). Le skill di usabilità (guided-setup, search-diagnose) e gli
script CI lo consumano; `exit_code` è anche nel JSON oltre che in `$LASTEXITCODE`.

## 3. Verifica della raggiungibilità del provider (opt-in, rete)

```powershell
sertor-rag doctor --online
```

In aggiunta agli statici, esegue un **probe minimale e non-indicizzante**: costruisce l'embedder
selezionato ed embedda una stringa sentinella. Riporta `reachable`/`unreachable` con il motivo. Senza
`--online` non c'è alcun traffico di rete. Non scarica mai il file GloVe e non indicizza.

## 4. Solo l'area config (cosa fa `configure --check`)

```powershell
sertor-rag doctor --area config --json
```

È il sottoinsieme che `sertor configure --check` invoca dietro le quinte.

## 5. Il wizard reso vivo

```powershell
sertor configure --check
```

Ora esegue una verifica config reale (via `doctor`) invece di «probe live non disponibile», e rimanda a
`sertor-rag doctor` per il quadro completo (provider/indice/MCP). `sertor configure` senza `--check`
resta identico a prima.

## Lettura dell'esito

| Area | fail (exit ≠ 0) | warn (exit 0) |
|------|-----------------|----------------|
| config | chiave env mancante → nominata + come fornirla | — |
| provider | config provider incompleta | irraggiungibile (con `--online`) / probe saltato |
| indice | assente o manifest incompatibile → `sertor-rag index .` | stantio (sorgenti modificate) → re-index suggerito |
| mcp | — | non registrato → come registrarlo; possibile stantio-dopo-reindex (riavvia il server) |
