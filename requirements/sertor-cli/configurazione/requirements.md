# Requisiti — Configurazione guidata (wizard) dell'ospite

<!-- Deriva da: FEAT-003 (epica sertor-cli) -->

> **Stato:** decomposizione **chiusa** — Q1–Q4 risolte con l'utente (2026-06-17, vedi §10). Pronta per
> `/speckit-specify`. Decisioni: **Q4 (a)** solo provider supportati dal core (Azure OpenAI/Ollama;
> store Chroma/Azure Search); **Q1 (a)** modalità ibrida CI-safe; **Q2 (a)** comando separato `sertor
> configure`; **Q3 (a)** validazione statica di default + `--check` live opzionale.

---

## 1. Contesto e problema (perché)

Dopo `sertor install rag`, sull'ospite resta `.sertor/.env` generato dal template di backend
(`packages/sertor/src/sertor_installer/assets/rag/env.{azure,local}.tmpl`) con i **segreti vuoti**:
oggi l'utente deve **aprire il file e compilarlo a mano** (endpoint Azure, API key, deployment di
embedding) sapendo quali variabili servono. Non c'è un percorso guidato: chi non conosce le manopole
`Settings` resta bloccato, e un valore sbagliato si scopre solo al primo `sertor-rag index`/`search`.

La **lettura** della configurazione è già consegnata (feature `esecuzione` + `Settings.load` +
`Settings.validate_backend`, che è la fonte unica statica di "quali campi servono per il backend
scelto"). Manca la **scrittura guidata**: un comando che (1) fa scegliere il provider di embedding e
lo store fra le opzioni **realmente supportate**, (2) raccoglie i valori (inclusi i segreti) e li
**scrive in `.sertor/.env`** in modo non distruttivo/idempotente, (3) **valida** che la
configurazione sia completa prima di dichiararla pronta. È l'anello che rende `install ≠ run`
percorribile da un utente reale senza editare a mano un file di ambiente.

**Vincolo di realtà (capacità del core, da non promettere oltre).** Il RAG di Sertor usa solo
**embeddings** (la generazione vive nell'assistente, non nel core). Provider di embedding supportati
oggi: **Azure OpenAI** (`RAG_BACKEND=azure`) e **Ollama** locale (`RAG_BACKEND=local`). Store
supportati: **Chroma** locale e **Azure AI Search**. La lista DA-6 dell'epica (OpenAI pubblico,
Anthropic, GitHub Copilot) e gli store PGVector/MongoDB **non esistono come adapter**; per di più
**Anthropic e Copilot non espongono un'API di embedding**, quindi non possono essere backend RAG. Il
wizard deve offrire **solo opzioni che il core onora**; estendere i provider/store è lavoro di core
(epica `backend-store-scala`), non di questa feature.

---

## 2. Obiettivi e criteri di successo

| ID | Criterio | Misura |
|----|----------|--------|
| CS-1 | **Configurazione completa senza editor** | Un utente porta un `.sertor/.env` da "segreti vuoti" a "pronto per l'indicizzazione" eseguendo un solo comando guidato, senza aprire manualmente il file. |
| CS-2 | **Validazione pre-uso** | Al termine, il comando dichiara la config **valida** se e solo se `validate_backend()` non riporta campi mancanti per il backend/store scelti; in caso contrario nomina i campi mancanti ed esce non-zero. |
| CS-3 | **Segreti mai versionati** | In **0** esecuzioni un segreto finisce in un file tracciato da git; i segreti vivono solo in `.sertor/.env` (già gitignored). |
| CS-4 | **Solo opzioni reali** | Il wizard propone esclusivamente i provider di embedding e gli store supportati dal core; in **0** casi offre un'opzione che `sertor-rag` non può poi onorare. |
| CS-5 | **Non distruttività & idempotenza** | Ri-eseguire la configurazione preserva i valori già presenti salvo conferma di sovrascrittura; due esecuzioni con gli stessi input producono lo stesso `.env`. |
| CS-6 | **CI-safe** | Il comando è eseguibile in modo **non interattivo** (tutti i valori via flag/ambiente) e non blocca mai in attesa di input quando non c'è un TTY. |
| CS-7 | **Local-only senza cloud** | Scegliendo il profilo locale (Ollama + Chroma) la configurazione si completa senza richiedere alcun valore di servizio cloud (REQ-E4). |

---

## 3. Stakeholder e attori

- **Maintainer dell'ospite**: configura il RAG sul proprio progetto subito dopo l'install.
- **Utente non esperto delle manopole `Settings`**: ha bisogno di una guida che sappia *quali*
  campi servono e *cosa* significano.
- **CI/automazione**: configura in modo non interattivo e deterministico.
- **`Settings` / `validate_backend`** (dipendenza): fonte unica di verità sui campi richiesti.
- **`sertor install rag`** (a monte): produce il `.sertor/.env` di partenza che il wizard compila.

---

## 4. Ambito

### In ambito

- Comando guidato di configurazione (`sertor configure` — Q2) che imposta su `.sertor/.env`:
  - il **provider di embedding** fra le opzioni supportate (Azure OpenAI / Ollama locale);
  - lo **store vettoriale** condizionale (Chroma locale / Azure AI Search), **ometibile** se la
    modalità non lo richiede (REQ-E7);
  - i **valori e i segreti** richiesti dal backend/store scelti.
- **Doppia modalità** (Q1): interattiva con prompt quando c'è un TTY; **completamente flag-driven**
  (non interattiva) per CI; mai bloccante senza TTY.
- **Validazione statica** della completezza via `validate_backend()` (Q3); **probe live opzionale**.
- Scrittura **non distruttiva/idempotente** in `.sertor/.env` (riuso del merge additivo esistente).
- Mascheramento dei segreti a video; nessun segreto negli output/log.
- Report umano e `--json` dell'esito (provider scelto, campi impostati, validazione).

### Fuori ambito

- **Aggiungere nuovi provider/store** (OpenAI pubblico, Anthropic, Copilot-embeddings, PGVector,
  MongoDB): è lavoro di core → epica `backend-store-scala`. **[ASSUNTO]**
- **Configurazione di capacità non-RAG** (wiki/governance non hanno provider da configurare).
- **Indicizzazione/esecuzione** del RAG: `install ≠ run`, resta a `sertor-rag index`.
- **Wizard di tutte le manopole opzionali** (`SERTOR_EMBED_CACHE`, `_OBSERVABILITY`, motore, graph,
  chunk-cap): restano commentate nel template; il wizard tratta solo ciò che serve a far girare il
  RAG. **[ASSUNTO — minimo vitale; le opzionali sono un'estensione Could]**
- **Gestione segreti esterna** (key vault, secret manager): fuori ambito.
- **Distribuzione del wizard su altri assistenti**: il comando è assistant-agnostico per costruzione.

---

## 5. Requisiti funzionali (EARS)

### 5.1 Selezione e raccolta

**REQ-001 (Event-driven):** *When the user runs the configuration command, the system shall present
the embedding-provider choices that the core actually supports (Azure OpenAI; Ollama local) and no
others.*

**REQ-002 (Event-driven):** *When the user selects a provider/store combination, the system shall
determine the exact set of configuration fields required for that combination from the same source
of truth used at runtime (`Settings.validate_backend`).*

**REQ-003 (Where — interactive):** *Where a TTY is available and no value was supplied via flag, the
system shall prompt for each required field, showing its name, a short description, and (if any) the
current value.*

**REQ-004 (Where — non-interactive):** *Where the command is run with all required values supplied
via flags/environment (or no TTY is present), the system shall complete without prompting and shall
not block waiting for input (CI-safe).*

**REQ-005 (Unwanted):** *If a required field has neither a supplied value nor an existing value and
no TTY is available to prompt, then the system shall fail with a non-zero exit code naming the
missing field(s), without writing a partial configuration.*

**REQ-006 (Optional):** *Where the user selects the local profile (Ollama + Chroma), the system
shall complete the configuration without requiring any cloud service value (REQ-E4).*

**REQ-007 (Optional):** *Where the selected RAG modality does not require a vector store, the system
shall allow configuration to complete without a store configured (REQ-E7); otherwise it shall
require a store.*

### 5.2 Scrittura e non distruttività

**REQ-010 (Event-driven):** *When the configuration is confirmed, the system shall write the values
into `.sertor/.env` using an additive, non-destructive merge that preserves unrelated lines and
comments.*

**REQ-011 (Unwanted):** *If a field already has a non-empty value in `.sertor/.env`, then the system
shall not overwrite it without explicit confirmation (interactive prompt or an explicit
`--overwrite`/`--force` flag).*

**REQ-012 (Ubiquitous):** *The system shall write secret values only into `.sertor/.env` (which is
git-ignored) and shall never write a secret into any version-controlled file (REQ-E5).*

**REQ-013 (Ubiquitous):** *The system shall mask secret values in all terminal output and structured
reports (no secret is ever echoed back or logged).*

**REQ-014 (Ubiquitous):** *Re-running the configuration command with the same inputs shall produce
the same `.sertor/.env` content (idempotency).*

**REQ-015 (Unwanted):** *If `.sertor/.env` does not exist when the configuration command runs, then
the system shall create it from the appropriate backend template before applying values (so the
command works even if `install rag` was not run first), without starting any RAG operation.*

### 5.3 Validazione

**REQ-020 (Event-driven):** *When configuration finishes, the system shall run the static validation
(`validate_backend`) and report whether the configuration is complete for the chosen backend/store.*

**REQ-021 (Unwanted):** *If static validation reports missing fields, then the system shall list them
and exit with a non-zero code, leaving the (partial) `.env` as written but clearly marked
incomplete.*

**REQ-022 (Optional):** *Where the user requests a live check (e.g. `--check`), the system shall
perform a minimal provider probe (a real embedding call) and report success/failure, separately from
the static validation; without the flag, no network call is made.*

**REQ-023 (Unwanted):** *If a live check is requested and fails, then the system shall report the
failure with an actionable message and a non-zero exit code, without discarding the written
configuration.*

### 5.4 Osservabilità e interazione

**REQ-030 (Ubiquitous):** *The system shall never start RAG ingestion or index creation as part of
configuration (install ≠ run).*

**REQ-031 (Event-driven):** *When configuration completes, the system shall emit a human-readable
summary (provider/store chosen, fields set, validation outcome) and, with `--json`, a
machine-readable report — neither of which contains secret values.*

**REQ-032 (Ubiquitous):** *The system shall exit with code `0` on a complete & valid configuration,
`1` on incomplete/invalid configuration or a failed live check, and `2` on wrong usage.*

---

## 6. Requisiti non funzionali

**NFR-01 (Sicurezza — segreti):** i segreti non lasciano mai `.sertor/.env`; non compaiono in
stdout/stderr, log o report; il mascheramento è applicato prima di qualunque emissione.

**NFR-02 (Non distruttività):** la scrittura riusa il merge additivo già usato da `install rag`
(`env_merge`), preservando righe/commenti non gestiti.

**NFR-03 (Host-agnosticità):** il comando funziona su qualunque ospite (Principio X); non presuppone
nulla oltre ai prerequisiti già richiesti da Sertor.

**NFR-04 (Fonte unica di verità):** l'insieme dei campi richiesti deriva da `Settings`/
`validate_backend`, non da una lista duplicata nel wizard (niente drift).

**NFR-05 (CI-safe & determinismo):** comportamento identico e non bloccante in assenza di TTY; nessun
prompt nascosto.

**NFR-06 (Coerenza con l'installer):** allineato alle convenzioni dei comandi `sertor` (flag
`--target`, `--json`, exit code, merge non distruttivi) introdotte da install/lifecycle.

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **install ≠ run**, non distruttività, idempotenza (invarianti dell'epica).
- **Solo provider/store supportati dal core** (Azure OpenAI, Ollama; Chroma, Azure AI Search).
- **Segreti solo in `.sertor/.env`** (REQ-E5), file già gitignored.
- Riuso di `Settings.validate_backend` e del merge `.env` esistente (no logica duplicata).

### Decisioni adottate (Q1–Q4 risolte 2026-06-17)

- **(Q1 a)** Modalità **ibrida CI-safe**: interattiva con TTY, flag-driven senza TTY (coerente
  con la decisione D4 di `lifecycle-installer`).
- **(Q2 a)** Comando **separato `sertor configure`** (non un'opzione di `install rag`):
  separa install da config, ed è ri-eseguibile per riconfigurare senza re-installare.
- **(Q3 a)** Validazione **statica di default** (`validate_backend`, offline), **probe live
  opzionale** dietro `--check` (mai rete di default — spirito install≠run).
- **(Q4 a)** Ambito provider = **solo embedding backend supportati dal core** (Azure/Ollama); la lista
  DA-6 più ampia è materia dell'epica `backend-store-scala`.

### Dipendenze

- `Settings` / `validate_backend` (`src/sertor_core/config/settings.py`).
- Template `.env` e `env_merge` del `sertor-install-kit` / `sertor_installer` (`install_rag`).
- Eventuale probe live → adapter di embedding del core (solo se Q3 include il live check).

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-01 | Promettere provider non supportati (DA-6) che il core non onora | Alta | Alto | CS-4/REQ-001: offrire solo opzioni reali; rinviare l'estensione a `backend-store-scala` |
| R-02 | Segreto trapelato in output/log | Bassa | Alto | NFR-01/REQ-013: mascheramento sistematico; riuso della redazione esistente |
| R-03 | Sovrascrittura di valori già impostati | Media | Medio | REQ-011: confronto + conferma/`--overwrite` |
| R-04 | Blocco in CI per prompt nascosto | Media | Medio | REQ-004/NFR-05: rilevare il TTY, fallire esplicito sui campi mancanti |
| R-05 | Probe live che costa/causa rete non voluta | Media | Basso | REQ-022: opt-in `--check`, mai di default |

---

## 9. Prioritizzazione (MoSCoW)

| Gruppo | Requisiti | Priorità |
|--------|-----------|----------|
| Selezione + raccolta (solo opzioni reali, fonte unica campi) | REQ-001, REQ-002, REQ-006, REQ-007 | **Must** |
| Doppia modalità CI-safe | REQ-003, REQ-004, REQ-005 | **Must** |
| Scrittura non distruttiva + segreti | REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015 | **Must** |
| Validazione statica + report + exit code | REQ-020, REQ-021, REQ-031, REQ-032, REQ-030 | **Must** |
| Probe live opzionale | REQ-022, REQ-023 | **Should** |
| Wizard delle manopole opzionali (cache/observability/engine) | (estensione) | **Could** |
| Estensione provider/store (OpenAI/PGVector/…) | (rinviato a `backend-store-scala`) | **Won't (qui)** |

---

## 10. Domande aperte — RISOLTE (2026-06-17)

Tutte chiuse con l'utente: **Q4 (a)** · **Q1 (a)** · **Q2 (a)** · **Q3 (a)**. Contesto originale sotto.

**Q4 — Ambito dei provider: confermare il taglio "solo ciò che il core supporta".** Il brief
dell'epica (DA-6) elenca OpenAI/Anthropic/Azure/Copilot/Ollama, ma il core oggi fa embedding solo con
**Azure OpenAI** e **Ollama**; Anthropic/Copilot non offrono embeddings. **Raccomandazione:** il
wizard configura **solo** Azure/Ollama (+ store Chroma/Azure Search); aggiungere provider è core
(`backend-store-scala`). *In alternativa,* includere **OpenAI pubblico** (embeddings `text-embedding-3`
via API non-Azure) se si vuole un terzo provider cloud — ma richiede un nuovo adapter, quindi
sconfina nel core.

**Q1 — Modalità d'interazione.** (a) Ibrida CI-safe *(racc.)* — prompt con TTY, flag-driven senza
TTY; (b) solo flag-driven (nessun prompt, massima semplicità ma meno "wizard"); (c) sempre
interattiva (rompe la CI). Coerenza con la scelta D4 di `lifecycle-installer` → (a).

**Q2 — Forma del comando.** (a) Nuovo **`sertor configure`** *(racc.)* — separato, ri-eseguibile;
(b) opzione/flag di `install rag` (es. `--configure`) — meno comandi ma accoppia install e config,
contro `install ≠ run`.

**Q3 — Validazione.** (a) Statica di default + **`--check` live opzionale** *(racc.)*; (b) solo
statica (più semplice, nessuna rete); (c) live sempre (costo/rete non voluti, viola lo spirito
install≠run).
