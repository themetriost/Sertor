# Quickstart — portabilità hook (Phase 1)

Come esercitare e **verificare la parità** (il gate). Il criterio di «fatto» è la parità provata
per-assistente + effetti di stato, su Windows/macOS/Linux, con i `.ps1` ritirati.

## 1. Invocazione di un hook portabile (manuale)

```bash
# simula un evento SessionStart per Claude (input JSON su stdin)
echo '{}' | uv run --no-project python .claude/hooks/rag-freshness-start.py --assistant claude
# atteso: JSON con additionalContext (o nulla se healthy), exit 0
```

## 2. Verifica di parità (il gate, offline)

```bash
uv run pytest packages/sertor/tests/test_portable_hooks_parity.py -q
# per ogni (hook × assistente): stdout == contratto atteso + file di stato .sertor/* nello schema atteso
# rete mockata (version-check); nessun pwsh richiesto
```

## 3. Fail-safe

```bash
# errore iniettato → exit 0 + breadcrumb secret-free
uv run pytest packages/sertor/tests/test_portable_hooks_parity.py -q -k "fail_safe or breadcrumb or stdin"
```

## 4. Smoke cross-OS (CI matrice)

```text
CI: ubuntu-latest + windows-latest → esegue ogni hook via `uv run --no-project python`, verifica exit 0
    (ubuntu NON ha pwsh → prova che i portabili non ne dipendono). I .ps1 NON girano in CI.
```

## 5. Ritiro `.ps1` + wiring (a parità verde)

```bash
# 0 .ps1 residui per gli 8 hook, 0 "shell":"powershell" nel loro wiring
git grep -l 'shell": "powershell"' packages/sertor/src/sertor_installer/assets/   # atteso: vuoto per gli 8
ls packages/sertor/src/sertor_installer/assets/rag/hooks/*.ps1                     # atteso: nessuno
```

## 6. Gate pre-merge (SC-006)

```bash
uv run pytest -m "not cloud"        # incl. parità + guardie sync aggiornate
uv run ruff check .
git diff --stat src/sertor_core/    # DEVE essere vuoto (core invariato)
```

## 7. Post-merge (dogfood)

Re-lock runtime → re-index → smoke MCP. Verifica dal vivo che gli hook portabili scattino sul dogfood
(Windows): SessionEnd → `.rag-health.json` aggiornato; PreToolUse → promemoria non-bloccante.

---

## Nota — dogfood è Windows

Il dogfood gira su Windows, dove i `.ps1` funzionavano: la **parità Windows** è provata dal dogfood stesso.
La parità **POSIX** (l'obiettivo) è provata dallo smoke CI ubuntu + dai test offline (host-agnostici).
