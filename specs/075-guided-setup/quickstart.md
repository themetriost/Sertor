# Quickstart — guided-setup (E12-FEAT-002)

Come si esercita la feature una volta implementata. Comandi **PowerShell** (Windows). La feature è
una **skill agentica** + distribuzione: il "quickstart" è in due piani — l'**uso** (l'agente esegue la
skill) e la **verifica di sviluppo** (deposito + parità, offline).

## A. Uso (l'agente dell'ospite esegue la skill)

Su un ospite con la capacità RAG installata (`sertor install rag`), l'utente chiede all'agente
frontier:

> «Metti su Sertor su questo repo» / «configura il RAG».

L'agente invoca la skill `guided-setup`, che:

1. lancia `sertor-rag doctor --json` (**sola lettura**) e rileva lo stato;
2. **propone** un provider dal contesto (creds cloud? airgapped? semantica NL?) e chiede conferma;
3. su conferma esegue `sertor install rag` (se manca), poi `sertor configure --set …` per riempire
   `.sertor/.env` (segreti via prompt sicuro, **mai** a schermo);
4. annuncia l'eventuale download GloVe una-tantum, poi su conferma `sertor-rag index .`;
5. rilancia `sertor-rag doctor` e dichiara **«verificato»** solo se verde; altrimenti espone area +
   rimedio (fail-loud).

Ri-eseguita su un ospite già configurato e sano: rileva, verifica, **non** ri-scaffolda (idempotenza).

## B. Verifica di sviluppo — deposito dual-target (offline)

```powershell
# Claude (default): skill in .claude/skills/, agente in .claude/agents/
uv run python -c "from pathlib import Path; from sertor_installer.install_rag import build_rag_plan; from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions; from sertor_install_kit.assistant import AssistantId; p=RagHostProfile.from_options(RagInstallOptions(target_root=Path('.'), backend='azure', with_deps=False)); plan=build_rag_plan(p, with_deps=False, assistant=AssistantId.CLAUDE); print([a.target_rel for a in plan if 'guided-setup' in a.target_rel or 'concierge' in a.target_rel])"
```

Atteso (Claude): `['.claude/skills/guided-setup/SKILL.md', '.claude/agents/concierge.md']`.
Con `AssistantId.COPILOT_CLI`: `['.github/skills/guided-setup/SKILL.md',
'.github/agents/concierge.agent.md']`.

## C. Verifica di sviluppo — suite di parità e deposito (offline)

```powershell
# parità: nessun leak .claude/ / slash-command / nome Claude (incluso model: sonnet) nei body Copilot
uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -q

# deposito dual-target: skill + agente; model: sonnet su Claude / assente su Copilot; routing a un ramo
uv run pytest packages/sertor/tests/test_install_rag.py -q -k "guided_setup or concierge"
```

Atteso: verde, offline (nessuna rete, nessun `uv` di rete, nessun ospite reale).

## D. Verifica di non-regressione (additività)

```powershell
# l'install RAG esistente è invariato salvo +1 skill +1 agente nel piano; sertor-core intatto
uv run pytest packages/sertor/tests/test_install_rag.py -q
uv run pytest -m "not cloud" -q   # core invariato
uv run ruff check .
```

## E. Confine D↔N (verifica concettuale)

La skill **non** importa `sertor_core`; orchestra solo i vehicle (`sertor install`, `sertor configure
--set`, `sertor-rag doctor`/`index`). La guardia di parità garantisce che il body non citi internals né
contenitori del target sbagliato. Nessun percorso runtime del core è alterato (additività, RNF-7).
