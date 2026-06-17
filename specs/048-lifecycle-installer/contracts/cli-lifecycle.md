# Contratto — comandi CLI di ciclo di vita (`upgrade` / `uninstall`)

**Feature**: `048-lifecycle-installer` (FEAT-008). Contratto dei nuovi sottocomandi dei due vehicles
(`sertor`, `sertor-flow`). Pattern di riferimento:
`packages/sertor/src/sertor_installer/__main__.py` e
`packages/sertor-flow/src/sertor_flow/__main__.py`.

**Exit code (comune, FR-005)**: `0` success (anche se tutto `skipped`/`removed`); `1` errore di dominio
(`SertorError`/`InstallerError`); `2` usage error (argparse o combinazione di flag vietata).

---

## A. `sertor upgrade [<capability> ...]`

```
sertor upgrade [wiki|rag|governance ...] [--assistant claude|copilot|copilot-cli]
               [--dry-run] [--json]
```

- **Argomento capacità (0..N).** Nessun argomento → **aggregato** = tutte le capacità installate
  (`wiki rag governance`), FR-032. Uno o più → solo quelle.
- `--assistant` (default `claude`, FR-003): seleziona il set di artefatti specifici dell'assistente.
- `--dry-run` (FR-001/FR-015): non scrive nulla; report con esiti **proiettati** (`updated`/`removed`/
  `skipped`).
- `--json` (FR-002): report `install.report/1` esteso (vedi `install-report-extended.md`).

**Semantica per capacità (FR-010..017):**
1. Costruisce il plan d'install della capacità per `--assistant` (UNICA fonte di verità, D2).
2. Per ogni artefatto applica la funzione inversa secondo `op=UPGRADE` (data-model §3):
   FILE→`update_file_if_changed`; MARKER_BLOCK→`update_marker_block`; merge/append/env→additivi
   idempotenti (NFR-05: i valori `.sertor/.env` mai sovrascritti).
3. **Fase obsoleti (diff a posteriori, D3):** path su disco in `sertor_owned_paths` ma assenti dal plan
   corrente → `removed`; path **non** Sertor-owned → `skipped` + **avviso** (FR-013), operazione
   continua.
4. Cambio assistente (FR-016): obsoleti = `owned(altri-assistenti su disco) − owned(--assistant)`; i
   path comuni restano.
5. `governance` → **puntatore** a `sertor-flow upgrade` (come install), nessuna dipendenza tra
   pacchetti; exit con messaggio dedicato.

**Idempotenza (SC-005):** upgrade su ospite allineato → exit `0`, `0 updated`, `0 removed`.

---

## B. `sertor uninstall [<capability> ...]`

```
sertor uninstall [wiki|rag|governance ...] [--assistant claude|copilot|copilot-cli]
                 [--dry-run] [--json] [--purge-wiki] [--yes]
```

- **Argomento capacità (0..N).** Nessun argomento → **aggregato** = tutte le installate
  (`sertor uninstall` ≡ `sertor uninstall wiki rag governance`), FR-032 / US8.
- `--assistant`, `--dry-run`, `--json`: come sopra.
- `--purge-wiki` (FR-027/028, solo capacità `wiki`/aggregato): abilita la rimozione della dir `wiki/`.
- `--yes` (FR-028): consenso esplicito non interattivo per `--purge-wiki`.

**Semantica per capacità (FR-020..031):**
- Tipo A (`.sertor/`, FR-030): `remove_path(".sertor")` in blocco → `removed`.
- Tipo B standalone (FR-020): `remove_path` di ogni `owned_file`/`owned_dir` (escluso `wiki/` salvo
  purge).
- Tipo C condivisi (FR-021/022/023): rimozione SOLO della porzione Sertor —
  `remove_marker_block` (blocco a marker), `remove_settings_entries` (hook con `command` Sertor),
  `remove_gitignore_lines` (`RUNTIME_IGNORES`); resto byte-per-byte invariato (NFR-01/FR-050).
- Tipo D MCP (FR-024/025): scope `local` → `deregister_mcp_client` (`claude mcp remove sertor-rag`;
  client assente → `McpRegistrationError` + fallback manuale); scope `project` → `remove_mcp_server`
  (file rimosso se conteneva solo `sertor-rag`, altrimenti solo la voce).
- Idempotenza (FR-026/SC-005): nessun artefatto presente → tutti `skipped`, exit `0`.
- `governance` → **puntatore** a `sertor-flow uninstall`.

**Regole `--purge-wiki` (decisione D4, deterministiche):**

| Combinazione | Comportamento |
|--------------|---------------|
| senza `--purge-wiki` | dir `wiki/` **preservata**; altri artefatti wiki rimossi (FR-027) |
| `--purge-wiki` + `--yes` | mostra `N pagine, ~K byte` poi rimuove `wiki/` → `removed` (SC-009) |
| `--purge-wiki`, TTY, no `--yes` | mostra conteggio + prompt `y/N`; no → wiki preservato, exit `0` |
| `--purge-wiki`, **no TTY**, no `--yes` | **non** rimuove; avviso azionabile («usa `--yes`»); exit `0` |
| `--purge-wiki` + `--dry-run` | **usage error, exit `2`** (non combinabili, FR-028) |
| `--purge-wiki` su `rag`/`governance` | usage error (flag valido solo per `wiki`/aggregato) |

---

## C. `sertor-flow upgrade` / `sertor-flow uninstall` (FR-040..045, US9)

```
sertor-flow upgrade   [--assistant claude|copilot] [--dry-run] [--json]
sertor-flow uninstall [--assistant claude|copilot] [--dry-run] [--json]
```

- Stessa semantica delle controparti `sertor` (FR-042), stesso schema report esteso.
- Operano sugli artefatti di governance: superfici Sertor-authored (`requirements-analyst`,
  `configuration-manager`, skill `requirements`), constitution starter, init/integration generati,
  blocco a marker `SERTOR:SDLC-RITUAL`, e `.specify/**` (da `specify init`).
- `uninstall`: rimuove SOLO il blocco `SERTOR:SDLC-RITUAL` dai file condivisi (FR-041); idempotente
  (FR-044). Constitution dell'ospite (`CREATE_IF_ABSENT`) **non** sovrascritta in upgrade.
- **Invariante:** `sertor-flow` non dipende da `sertor-core`/`sertor` (FR-045/FR-055); riusa SOLO le
  primitive del kit (FR-053).
- `runner` iniettabile (come `install`, per mock di `claude mcp remove` / `specify` senza rete).

---

## D. Osservabilità (FR-007/FR-040 della fonte)

A fine operazione ogni comando emette `log_event(level, operation, capability=..., assistant=...,
updated=..., removed=..., skipped=..., errors=...)` con `operation ∈ {"upgrade", "uninstall"}`
(kit `observability.log_event`, già usato da `install rag`). Nessun segreto nei campi.

---

## E. Contratti delle primitive inverse del kit (`install-kit/1` esteso)

Funzioni pure/stdlib nel `sertor-install-kit`, duali 1:1 delle additive esistenti (FR-053):

| Funzione | Firma (sintetica) | Garanzia |
|----------|-------------------|----------|
| `remove_marker_block` | `(path, marker_start, marker_end) -> Outcome` | toglie SOLO il blocco; fuori invariato byte-per-byte; marker assenti → `SKIPPED` |
| `update_marker_block` | `(path, content, m_start, m_end) -> Outcome` | dentro-marker = bundle se differiva (`UPDATED`); uguale → `SKIPPED`; assente → `BLOCK` |
| `remove_settings_entries` | `(path, fragment) -> (Outcome, detail)` | toglie SOLO hook con `command` nel fragment; altre voci intatte |
| `remove_gitignore_lines` | `(path, lines=RUNTIME_IGNORES) -> (Outcome, detail)` | toglie SOLO le linee note + header; altre intatte |
| `remove_mcp_server` | `(path, server="sertor-rag", root_key) -> (Outcome, detail)` | toglie SOLO la voce; file rimosso se era l'unica; altri server intatti |
| `deregister_mcp_client` | `(runner, server="sertor-rag") -> Outcome` | `claude mcp remove`; client assente → `McpRegistrationError` + fallback |
| `update_file_if_changed` | `(dest, content) -> Outcome` | differente → `UPDATED`; uguale → `SKIPPED`; assente → `CREATED` |
| `remove_path` | `(dest) -> Outcome` | rimuove file/albero; assente → `SKIPPED` (idempotenza) |

Tutte: stdlib-only (NFR-07), non sollevano per assenza (idempotenza), non toccano nulla fuori dal
`target_rel` indicato (FR-031/FR-050).
