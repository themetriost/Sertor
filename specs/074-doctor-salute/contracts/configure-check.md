# Contract — `sertor configure --check` cablato su `doctor` (E12-FEAT-001, scope `sertor`)

Chiude il debito *deferred* E2/FEAT-003 US5. Il punto d'estensione esiste già
(`packages/sertor/src/sertor_installer/configure.py::_probe_live`, riga 369) e oggi degrada onestamente
perché invoca `sertor-rag check` (inesistente). Questa feature lo rende **operativo** cambiando il
comando invocato in `sertor-rag doctor` come **sottoinsieme config** (DA-D3).

## Cambiamento (additivo, FR-016/017/018)

`_probe_live` invoca:

```
sertor-rag doctor --area config --json    (cwd = target_root)
```

invece di `sertor-rag check`. Mapping esito → `LiveCheckOutcome(requested, ok, detail)`
(`configure_report.py:58`):

| Esito subprocess | `ok` | `detail` |
|------------------|------|----------|
| comando assente / `unknown command` / exit 2 | `None` | «probe live non disponibile in questa versione del runtime …» (degrado onesto preservato, US8.3) |
| exit 0 | `True` | «config ok — esegui `sertor-rag doctor` per il quadro completo (provider/indice/MCP)» |
| exit ≠ 0 (config incompleta) | `False` | messaggio config dal JSON, già scrubbed (`mask_secret_free`) |

## Invarianti

- `configure` **senza** `--check` resta **byte-identico** a oggi (FR-017/SC-011): l'unico percorso
  toccato è `_probe_live` + la stringa del comando.
- Degrado onesto preservato (FR-018): se `doctor`/`sertor-rag` non è sul runtime, `--check` non va in
  crash (`ok=None`).
- `--check` è un **sottoinsieme config**, non un alias dell'intero `doctor` (DA-D3): rimanda
  esplicitamente a `doctor` per provider/indice/MCP.
- Principio XI: invocazione via subprocess del vehicle, mai `import build_embedder`/`build_*` dal
  wizard.

## Test (suite `sertor`)

- `_probe_live` con `FakeCommandRunner` che ritorna exit 0 / exit 1 (JSON config-incompleto) / exit 2 /
  `is_available=False` → i quattro `LiveCheckOutcome` attesi;
- `configure` senza `--check` → nessuna invocazione del runner (regression guard FR-017).
