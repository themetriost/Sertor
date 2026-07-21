---
title: "doctor — la diagnostica di salute deterministica"
type: tech
tags: [diagnostica, usabilita, sertor-rag, deterministic, vehicle, principio-x, principio-xi, principio-xii, feat-074, feat-038]
created: 2026-07-21
updated: 2026-07-21
sources: ["src/sertor_core/cli/__main__.py", "src/sertor_core/services/doctor.py", "specs/074-doctor-salute/plan.md", "specs/106-feat-038-doctor-ancorato-root/plan.md", "wiki/experiments/feat-074-doctor-salute.md", "docs/troubleshooting.md"]
---

# doctor — la diagnostica di salute deterministica

`sertor-rag doctor` è il comando che risponde a **«ha funzionato?»** dopo aver installato e configurato
Sertor su un ospite — in un colpo solo, senza LLM, senza scrivere nulla. È il **primitive
deterministico** dell'epica E12 `usabilità` (FEAT-074, PR 2026-06-23): dove un agente potrebbe *inventare*
una diagnosi, `doctor` la **misura**. Sta dal lato N del confine [[deterministic-vs-judgment|meccanico↔giudizio]]:
è sola lettura, zero-LLM, e il suo verdetto è riproducibile bit-per-bit.

## Le quattro aree

`doctor` diagnostica **quattro aree** ortogonali del setup, ciascuna con un esito **pass/warn/fail** e —
quando non è `pass` — **causa + rimedio concreto** (non «qualcosa non va», ma *quale* var manca e *come*
riempirla):

| Area | CRITICO (fail) | WARN | OK (pass) |
|------|----------------|------|-----------|
| **config** (env/config) | var env obbligatoria mancante | — | presente e valida |
| **provider** (embeddings) | key del provider mancante | irraggiungibile (probe fallita, solo con `--online`) | raggiungibile o probe non richiesta |
| **index** (indice RAG) | assente o incompatibile (provider diverso, `logic_version` stantio) | stantio (mtime cambiato **e** content-hash diverso) | fresco e compatibile |
| **mcp** (server MCP) | — | non registrato **o** richiede riavvio | registrato e funzionante |

Il rollup è semplice e onesto: **exit 0** se tutte le aree sono ≥ WARN, **exit 1** se almeno una è
CRITICA. L'exit-code è un **gate** — uno script (o il wizard `configure --check`) può ramificare sul
verdetto senza parsare testo. `--area {config,provider,index,mcp,all}` restringe le aree eseguite
(`config` è il sottoinsieme usato da `configure --check`); `--json` emette lo schema stabile.

## Offline-safe by default, probe opt-in

**Di default `doctor` non tocca la rete**: verifica la struttura statica della config (via
`Settings.validate_backend()`), non scarica mai il modello GloVe, non embedda nulla. La verifica di
*raggiungibilità* del provider è **opt-in dietro `--online`**: solo allora `doctor` costruisce
l'embedder (via il vehicle `build_provider_probe`, mai `import` diretto — Principio XI) ed embedda una
sentinella breve. Provider irraggiungibile ⇒ **WARN** (exit 0), col rimedio nominato («configura
`AZURE_OPENAI_API_KEY`» o «avvia Ollama»). Questa scelta rende `doctor` sicuro da eseguire in CI e in un
loop, senza costo né effetti collaterali.

Sul rilevamento **MCP-stantio** `doctor` non finge: il segnale cross-processo forte non è oggi
osservabile (il server MCP è out-of-process), quindi al più emette un WARN *debole* (indice stantio +
MCP registrato → «potrebbe servire un indice non fresco, riavvia il server») e, in assenza di segnale,
riporta `unknown` invece di inventare uno stato (Principio XII, *fail-loud / non mentire*). Il self-check
di freschezza *dentro* il server resta un debito promosso.

## Il contratto `doctor.report/1`

`--json` emette lo schema stabile **`doctor.report/1`**: le quattro aree, ciascuna col suo stato e la
lista dei `Problem` (title, description, severity, remedies), più il verdetto complessivo e l'exit-code.
È il **contratto macchina-leggibile** su cui si appoggiano i consumatori: `sertor configure --check`
delega proprio a `sertor-rag doctor --json`, e l'hook `rag-freshness` lo usa come misura (vedi sotto).
L'osservabilità è **metrics-only** (evento `doctor`: conteggi per severità, exit-code, se online) —
mai una var, un path, una query o un segreto.

## Ancorato alla radice (FEAT-038)

Un verdetto di salute deve essere lo **stesso da qualunque directory** lo si invochi — altrimenti non è
una misura, è un artefatto del cwd. Fino a E10-FEAT-038 (2026-07-18) `_cmd_doctor` fissava
`root = Path.cwd()`: il manifest si caricava bene ovunque (via `settings.index_dir` self-localizing), ma
le sorgenti e `.mcp.json` venivano ri-risolti contro il cwd → **`index: pass` dalla root e `index: warn`
da `src/`**, `registered` che oscillava. Il fix introduce `Settings.project_root`, risolto con la
**stessa** self-localization di `.env`/`.index` (`CLAUDE_PROJECT_DIR` se valido, altrimenti il parent
della `.sertor/` che possiede l'indice risolto via `sys.prefix`, altrimenti `None` → **fail-loud** prima
di stampare qualunque verdetto). Ora `doctor` concorda con `index`/`search`: una sola semantica di root
nel CLI, invarianza provata LIVE sul runtime installato.

Complementare a questo, il fix di freschezza (branch 076): l'indice è marcato `stale` **solo** se
*mtime cambiato AND content-hash diverso* — così le operazioni git (checkout/merge/pull), che ri-bumpano
gli mtime a contenuto identico, non generano più falsi `index_stale` cronici, allineando `doctor` alla
logica dell'indicizzatore incrementale.

## Ruolo: verifica del guided-setup, misura del rag-freshness

`doctor` non vive isolato: è il **passo di verifica** di due meccanismi.

- **Guided-setup** (E12): la skill `guided-setup` porta un repo da non-configurato a un
  **`sertor-rag doctor` verde** — è la sua condizione di successo, il segnale fail-loud che chiude
  l'onboarding (vedi [[feat-075-guided-setup]]).
- **rag-freshness hook** (E10-FEAT-034, 2026-07-20): l'hook `SessionEnd` usa `doctor` come **misura**
  nel ciclo **misura → ripara → rimisura → persisti**. Prima misurava *prima* del re-index (verdetto
  pre-riparazione, che allarmava anche nel caso normale); ora esegue re-index (ripara) → `doctor`
  (rimisura) → scrittura atomica del verdetto **post-riparazione** in `.sertor/.rag-health.json`. Questo
  ciclo è stato possibile **solo dopo** l'ancoraggio alla radice: un `doctor` cwd-dipendente non è una
  misura affidabile.

Il complemento **statico** di `doctor` è `docs/troubleshooting.md`: `doctor` dà la diagnosi *dinamica*
sullo stato reale, la doc dà la guida *statica* di rimedio. Come [[dogfood-fidelity|client fedele]] di
sé stesso, il dogfood esercita `doctor` a ogni chiusura di step (parte dello smoke-test del rituale).

Vedi anche: [[mcp-server]] · [[deterministic-vs-judgment]] · [[feat-075-guided-setup]] · [[dogfood-fidelity]].
