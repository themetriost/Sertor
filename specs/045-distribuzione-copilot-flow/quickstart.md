# Quickstart — Governance Sertor su un ospite GitHub Copilot (FEAT-009)

Come un team Copilot installa il **metodo SDLC** di Sertor (SpecKit + requisiti + delega git +
costituzione + rituale) sul proprio repo. Gemella di FEAT-007 (che copre RAG+wiki).

## 1. Installazione (install ≠ run)

```bash
sertor-flow install --assistant copilot
```

Senza `--assistant` → default `claude`. Nessuna fase SpecKit parte da sola. Richiede l'installer di
spec-kit raggiungibile (a versione pinnata): se manca, l'installazione **fallisce con istruzioni**, non
lascia nulla a metà.

## 2. Cosa compare nel repo (target copilot)

```text
.github/prompts/speckit.*.prompt.md      # comandi SpecKit (da `specify init --ai copilot`)
.github/agents/*.agent.md                # agenti SpecKit + requirements-analyst + configuration-manager
.github/prompts/requirements.prompt.md   # skill requirements (Sertor-authored, resa)
.github/copilot-instructions.md          # blocco rituale SDLC (marker SERTOR:SDLC-RITUAL)
.specify/**                              # macchinario SpecKit condiviso (agent-agnostic)
.specify/memory/constitution.md          # costituzione-starter (identica per ogni assistente)
```

## 3. Verifica

1. I comandi `/speckit.*` (specify/plan/tasks/…) sono invocabili dal client Copilot.
2. Gli agenti `requirements-analyst` e `configuration-manager` esistono come custom-agent Copilot.
3. Il blocco rituale SDLC è in `.github/copilot-instructions.md`.
4. La costituzione-starter è presente e identica a quella che otterrebbe un utente Claude.

## 4. Non-regressione e coesistenza

- `sertor-flow install --assistant claude` produce la governance **come prima** (stessi comandi/agenti
  SpecKit + `.specify/`), solo ottenuta lanciando `specify init` invece che da copie vendorate.
- Su uno stesso repo, governance per Claude e Copilot coesistono (`.claude/**`+`CLAUDE.md` vs
  `.github/**`) senza conflitti.
- Ri-eseguire l'install → tutto `skipped`/`block già presente` (idempotente).

## 5. Combinato con FEAT-007

Un ospite Copilot può avere **entrambe**: `sertor install <wiki|rag> --assistant copilot` (RAG+wiki) e
`sertor-flow install --assistant copilot` (governance) — stesso meccanismo `--assistant`, condiviso nel
`sertor-install-kit`.
