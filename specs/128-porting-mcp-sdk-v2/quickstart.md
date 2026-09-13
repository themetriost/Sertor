# Quickstart — verificare il porting a mano

**Feature**: 128-porting-mcp-sdk-v2 · **Data**: 2026-09-13

Comandi in **PowerShell** (convenzione del repo). Ogni blocco dice **cosa deve succedere**: se succede
altro, è un difetto, non una variante.

## 1. Le due linee esistono e la selezione funziona

```powershell
uv run python -c "from sertor_mcp._sdk import SDK_LINE, ServerClass, ToolError; print(SDK_LINE, ServerClass.__name__, ToolError.__module__)"
```

**Atteso:** la linea risolta dal lock del workspace, il nome della classe server, il modulo della classe
d'errore. Nessuna eccezione.

Ora la linea **opposta**, senza toccare il lock:

```powershell
uv run --with "mcp==2.2.0" --no-project python -c "from sertor_mcp._sdk import SDK_LINE; print(SDK_LINE)"
uv run --with "mcp==1.29.0" --no-project python -c "from sertor_mcp._sdk import SDK_LINE; print(SDK_LINE)"
```

**Atteso:** `v2` e `v1`. Se stampa lo stesso valore due volte, l'ambiente non ha cambiato linea e
**qualunque verifica successiva è vuota** — è il difetto che il primo test del passo CI presidia.

## 2. Il server parte e serve i dieci tool

```powershell
uv run --project .sertor sertor-rag doctor
```

**Atteso:** `PASS`. ⚠️ **Attenzione, e vale la pena saperlo:** questo comando dice `mcp pass` guardando la
**registrazione** in `.mcp.json`, **non** l'avvio — quindi resta verde anche con il server morto
(**E10-FEAT-072**, aperta). Non usarlo come prova che il server funziona: serve solo a dire che è
registrato.

La prova vera è il test di contratto, che parla il protocollo:

```powershell
uv run pytest tests/contract/test_mcp_protocol_e2e.py -v
```

**Atteso:** handshake completato, dieci nomi di tool, payload di un tool `list[dict]` nella forma
`{"result": [...]}`.

## 3. Un guasto previsto porta la sua diagnosi

È il cuore della feature. Si esercita puntando il server a un corpus **senza indice**:

```powershell
$env:SERTOR_CORPUS = "corpus-che-non-esiste"
uv run pytest tests/contract/test_mcp_protocol_e2e.py -k diagnostic -v
Remove-Item Env:\SERTOR_CORPUS
```

**Atteso:** l'esito d'errore porta `isError: true` e un contenuto che **nomina la causa** (indice assente)
e il rimedio, non solo il nome del tool. Su **entrambe** le linee.

## 4. Le due linee, sulla suite

```powershell
uv run pytest tests/unit/test_mcp_server.py tests/unit/test_mcp_graph_tools.py tests/unit/test_mcp_combined_graph.py tests/unit/test_score_contract.py tests/unit/test_doctor.py tests/unit/test_single_venv_guard.py -q
uv run --with "mcp==2.2.0" --no-project pytest tests/unit/test_mcp_server.py -q
```

**Atteso:** verde in entrambi i casi. Il secondo comando è quello che oggi **non esiste** in CI e che il
piano aggiunge.

## 5. Il vincolo è coerente nei due punti

```powershell
Select-String -Path pyproject.toml -Pattern 'mcp>=' | ForEach-Object { $_.Line.Trim() }
```

**Atteso:** due righe, **stesso intervallo** (`mcp>=1.2,<2.3`), ciascuna con il commento che nomina la
versione misurata e la condizione per alzare il tetto.

## 6. Lo scenario dell'ospite colpito (SC-005)

Non è verificabile sul dogfood — il suo runtime insegue l'ultimo commit e non ri-risolve mai le
dipendenze. Si misura **solo** sull'host usa-e-getta dell'upgrade smoke:

```powershell
gh workflow run "upgrade smoke (full)" -f from_ref=v0.4.1
```

**Atteso:** fra gli esiti richiesti per nome compare **`OK   mcp-server-imports`**, e il log mostra che
*prima* dell'upgrade l'import **falliva** (la condizione piantata). Se quel «prima falliva» non c'è,
l'esito è passato gratis e non ha misurato nulla.

## Gate pre-merge (obbligatorio, sette comandi + lint)

```powershell
uv run pytest -m "not cloud" -q
uv run pytest packages/sertor/tests -m "not cloud and not integration and not hooks_smoke" -q
uv run pytest packages/sertor/tests -m hooks_smoke -q
uv run pytest packages/sertor-install-kit/tests -q
uv run pytest packages/sertor-flow/tests -q
uv run pytest packages/speclift/tests -q
uv run pytest packages/specaudit/tests -q
uv run ruff check .
```

**Nota:** `-m hooks_smoke` **richiede il percorso** `packages/sertor/tests`; lanciato dalla radice senza
percorso deseleziona tutto ed esce 0 — un comando di gate che verifica nulla.
