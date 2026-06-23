# Contract — skill `guided-setup`

Asset di istruzioni host-agnostico eseguito dall'**agente frontier dell'ospite**. Orchestra i vehicle
deterministici; **non** reimplementa comandi, **non** importa `sertor_core` (Principio XI/D↔N). Body
**inglese** byte-identico tra Claude e Copilot; riferimento-per-nome agli asset/vehicle.

> **Rapporto con l'agente `concierge`** (vedi `agent-concierge.md`): la skill porta il **«come»** (il
> flusso). L'agente `concierge` è la **persona/orchestratore** (con `model: sonnet` su Claude) che
> instrada le richieste di setup **verso questa skill**. La skill è invocabile **anche** a sé
> (pattern `eval-suite-author`); l'agente è il dispatcher che la richiama.

## Frontmatter (nativo agent-skill, valido su entrambi i target)

```yaml
name: guided-setup
description: "Guide the user from an unconfigured repo to a verified Sertor RAG (a green
  `sertor-rag doctor`), conversing and orchestrating ONLY the deterministic vehicles
  (`sertor install`, `sertor configure --set`, `sertor-rag doctor`/`index`). Detects current state,
  recommends an embedding provider from context (with confirmation), fills `.env` securely (never
  printing secrets), announces the one-time GloVe download, and verifies fail-loud via `doctor`.
  Read-only checks run freely; every host mutation/download runs only after explicit confirmation.
  It never reimplements a command and never imports the core."
user-invocable: true
disable-model-invocation: false
```

## Input

L'intento «set up Sertor / configure the RAG» innesca la skill. Testo vuoto → la skill chiede di
descrivere l'obiettivo (configurare il RAG su questo repo).

## Flusso (contratto comportamentale)

| Step | Tipo | Vehicle | Gate |
|------|------|---------|------|
| 1. Detect | **sola lettura** | `sertor-rag doctor --json` (+ ispezione read-only di `.sertor/.env`) | libero (no conferma) |
| 2. Provider | conversazione | euristica (vedi sotto) | proposta + **conferma** |
| 3. Install | **mutante** | `sertor install rag [--assistant <host>]` | **conferma esplicita** |
| 4. Configure | **mutante** | `sertor configure --set KEY=VALUE` / prompt sicuro | **conferma esplicita**; segreti via `getpass` |
| 5. Index | **mutante / download** | `sertor-rag index .` | **conferma esplicita**; annuncio GloVe se non in cache |
| 6. Verify | **sola lettura** | `sertor-rag doctor` | libero; gate del «successo» |

### Idempotenza (FR-009, US7)

Step 1 determina cosa manca dalle 4 aree del report `doctor.report/1` (`config`/`provider`/`index`/
`mcp`). Se **tutte verdi** → dichiara «già configurato e verificato», **non** ri-scaffolda, si ferma.
Se **parziale** → conduce **solo** i passi mancanti. Mai duplicazione di artefatti già presenti.

### Euristica provider (Step 2 — FR-004/005, DA-G2)

3 segnali, letti **via vehicle/file** (mai core):
1. **Creds cloud presenti?** — area `config`/`provider` di `doctor --json` (chiavi `AZURE_OPENAI_*`
   mancanti = no creds), o ispezione read-only di `.sertor/.env`/ambiente.
2. **Airgapped?** — segnale conversazionale, o `doctor --online` → provider `unreachable`.
3. **Serve semantica NL?** — la skill **chiede** (corpus ricco di documentazione?).

Regole (proposta + conferma, mai imposizione):
- creds assenti O airgapped → **locale** (`glove` se serve NL — default core; `hash` per il pavimento
  airgapped/deterministico), con motivazione;
- creds presenti + NL → propone **cloud** (Azure) con motivazione, o `glove` se on-machine preferito;
- **sempre** l'utente conferma; nessuna selezione automatica.

Il provider scelto entra in `.env` allo Step 4 via `sertor configure --set SERTOR_EMBED_PROVIDER=…`.

### Segreti (Step 4 — FR-006, RNF-3, US3)

- raccolti **solo** via `sertor configure --set`/prompt `getpass` del wizard;
- il valore **non** è mai stampato (né a schermo né nei log della conversazione);
- segreto già presente in `.env` → **non** ri-richiesto né esposto.

### Download GloVe (Step 5 — FR-007, US4)

provider `glove` + modello non in cache → la skill **annuncia** il download una-tantum (~822 MB)
**prima** di lanciare l'index. Cache presente → nessun annuncio. Degrado onesto: solo annuncio finché
FEAT-003 (progress) non esiste.

### Verify fail-loud (Step 6 — FR-002/003, RNF-4, Principio XII)

- `doctor: PASS` (exit 0) → dichiara «verificato», riportando l'esito a supporto;
- non verde → espone **area + rimedio** dalle righe del report (es.
  `provider FAIL provider config incomplete (AZURE_OPENAI_API_KEY)`) e **non** dichiara successo.

## Output atteso

Conversazione che termina con uno di due esiti:
- **verificato**: `doctor` verde + sintesi dei passi condotti;
- **non verificato**: area(e) in errore + rimedio azionabile, **nessun** claim di successo.

In **nessun** output compare un valore di segreto.

## Invarianti (test)

- nessun `.claude/` path / slash-command / nome-prodotto Claude nel body (guardia parità);
- nessun import di `sertor_core` / `build_*` prescritto dal body (D↔N);
- ogni mutazione preceduta da conferma; check read-only liberi;
- nessun «fatto» senza `doctor` verde.
