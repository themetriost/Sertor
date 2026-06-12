# Quickstart — `sertor install rag`

Portare la capacità RAG su un repo ospite (Python o non-Python) con **un comando**, senza conoscere
gli internals. Presuppone solo `uv` installato sulla macchina.

## Caso tipico (Azure, da una sessione Claude su un altro progetto)

```bash
# nella radice del repo ospite (oppure --target <path>)
uvx --from "git+https://github.com/themetriost/Sertor.git#subdirectory=packages/sertor" \
    sertor install rag --backend azure
```

Cosa lascia sul progetto (install ≠ run — nessuna indicizzazione):
- `.sertor/` con l'ambiente Python isolato e `sertor-core[azure,mcp,graph,rerank]` installato;
- `.sertor/.env` col template Azure (riempi i segreti: endpoint, API key);
- `.mcp.json` in radice (il server `sertor-rag` che Claude interroga);
- `.gitignore` aggiornato (artefatti rigenerabili ignorati).

Poi, quando vuoi (passo esplicito separato):
```bash
# 1) riempi i segreti in .sertor/.env, poi indicizza i sorgenti host (esclude .sertor/)
uv run --directory .sertor sertor-rag index ..
# 2) ricarica Claude Code: approva il server sertor-rag → search_code/docs/combined (+ grafo)
```

## Varianti
```bash
# backend locale (Ollama), niente reranker, report JSON
sertor install rag --backend local --no-rerank --json

# solo scaffold di config, senza toccare le dipendenze
sertor install rag --no-deps

# corpus esplicito e target esplicito
sertor install rag --target C:\path\MyApp --corpus myapp
```

## Idempotenza
Rieseguire è sicuro: i file esistenti non vengono sovrascritti (merge additivo), le voci non
duplicate; la seconda passata riporta solo `skipped`/`merged`. Disinstallare ≈ cancellare `.sertor/`
e la voce `sertor-rag` da `.mcp.json`.

## Esito atteso (report)
```
sertor install rag — target: /path/MyApp
  created .sertor (uv add sertor-core[azure,mcp,graph,rerank] @ git+…)
  created .sertor/.env (backend=azure, segreti vuoti)
  created .mcp.json (server sertor-rag)
  merged  .gitignore (+3 voci)
Riepilogo: 3 creati · 0 saltati · 1 merged · 0 errori
```

## Note di prerequisito
- **`uv` assente** → il comando si ferma con un messaggio che chiede di installarlo (exit 1).
- **Macchina pulita + `uvx`**: richiede il fix di distribuzione (R1) **pushato** sul remoto; in
  sviluppo locale si usa `uv run sertor install rag` dal workspace.
