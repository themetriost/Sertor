# Contract — model-policy profile & Copilot custom-agent rendering

Contratti offline-verificabili (nessuna rete, nessun tenant Copilot reale — RNF-7). Sono la base dei
test riconciliati e nuovi.

## C1 — `resolve_model(agent_name)` (kit `model_policy.py`)

```
resolve_model: str -> str
```

- **R1 (copertura).** Per ognuno dei 5 nomi in ambito (`concierge`, `configuration-manager`,
  `requirements-analyst`, `requirements`, `wiki-curator`) ritorna un model-ID non-vuoto.
- **R2 (determinismo).** Stessa versione del profilo → stesso ID, indipendente da env/rete (NFR-002).
- **R3 (fail-loud nominante).** Per un nome non presente solleva `ModelPolicyError` il cui messaggio
  **contiene** il nome mancante (FR-008). *Anti-pattern:* mai ritornare `None`/`""`/default silenzioso.
- **R4 (fonte unica).** Ogni model-ID compare **solo** in `_MODEL_POLICY`; 0 ID letterali per-agente
  nel codice di deposito (grep-guard concettuale via il test di coerenza, CS-3).
- **R5 (versione).** `MODEL_POLICY_VERSION` è un marcatore stringa; un bump di ID è distinguibile da
  una modifica di persona (FR-007/NFR-004).

## C2 — `render_custom_agent(canonical, *, model)` (kit `surfaces.py`)

```
render_custom_agent: (str, model: str|None) -> str
```

- **R6 (omissione senza policy).** `model=None` → il frontmatter reso NON contiene `model:`
  (retrocompat; comportamento odierno).
- **R7 (sostituzione con policy).** `model="<id>"` → il frontmatter contiene esattamente `model: <id>`,
  **al posto** di qualunque `model:` presente nel canonico.
- **R8 (no leak alias Claude).** Il valore `model:` reso non è mai un **alias Claude nudo**
  (`haiku`/`sonnet`/`opus`). *Nota:* la verifica è sul **valore parsato** della riga `model:`, non
  su una sottostringa (un ID valido come `claude-haiku-4.5` contiene `haiku` ed è lecito).
- **R9 (persona intatta).** `name`/`description`/`tools` e il body sotto il frontmatter sono preservati
  verbatim (anti-drift, FR-003); `_yaml_scalar` invariato (quoting delle description con `:`).

## C3 — Deposito reale sui 5 agenti (offline, `tmp_path`)

Eseguendo `build_rag_plan` + `build_install_plan` (wiki) + `build_governance_plan` per
`AssistantId.COPILOT_CLI` e applicando in `tmp_path`:

- **R10 (default esplicito).** I 5 `.agent.md` hanno ciascuno un `model:` esplicito non-vuoto pari a
  `resolve_model(<name>)` (CS-1). 0 agenti a selezione implicita.
- **R11 (no leak).** Nessuno dei 5 frontmatter contiene un alias Claude nudo (CS-2).
- **R12 (fail-loud profilo incompleto).** Con un profilo sintetico privo di una voce in ambito, il
  **build del piano** solleva `ModelPolicyError` nominante e **nessun** file è scritto (CS-5, FR-009).
- **R13 (idempotenza).** Ri-render/upgrade a parità di versione profilo → contenuto byte-identico
  (CS-4, FR-010).

## C4 — Isolamento Claude

- **R14 (Claude invariato).** I 5 frontmatter Claude resi/depositati (byte-copia `.claude/**`) sono
  bit-per-bit identici al baseline, incluso il `model: sonnet` di `concierge` (CS-7, FR-012). Il
  parametro `model` del renderer non è usato sul path Claude.

## C5 — Coerenza cross-pacchetto & confini

- **R15 (coerenza).** `sertor` e `sertor-flow` importano lo stesso `model_policy` → stesso ID per lo
  stesso agente (FR-004/CS-3), senza dipendenza `sertor-flow`→`sertor-core`.
- **R16 (speckit.* fuori ambito).** I prompt-file `speckit.*` depositati per Copilot non ricevono
  `model:` (FR-017).
