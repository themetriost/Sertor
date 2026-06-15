# sertor-flow

Installer of Sertor's **development method (SDLC)** on a host repository: SpecKit flow, requirements
management, git delegation, constitution-starter, SDLC ritual block. Separate package, orthogonal to
the RAG, **with no dependency on `sertor-core`** (the installer machinery comes from
`sertor-install-kit`).

## Install (install ≠ run)

```bash
sertor-flow install [--assistant claude|copilot] [--target <path>] [--json]
```

- `--assistant` (default `claude`): target AI assistant. `claude` writes under `.claude/**` +
  `CLAUDE.md`; `copilot` writes under `.github/**` (prompts, agents, `copilot-instructions.md`).
  An unknown value is rejected with an explicit error.
- `--target` (default cwd): the host repo root.
- `--json`: emit the install report as JSON.

`install ≠ run`: the command only deposits the bundle — it never starts an SDLC/git/index phase.

## SpecKit via launch-installer (feature 045)

`sertor-flow` **no longer vendors SpecKit**. It obtains the SpecKit commands/agents and the
`.specify/**` machinery by **launching the spec-kit installer** for the target assistant, at a
pinned upstream version:

```
uvx --from git+https://github.com/github/spec-kit.git@v<version> specify init . --here \
    --ai <assistant> --script <ps|sh> --no-git --force
```

This follows spec-kit's first-class per-assistant variants (Claude/Copilot) instead of vendoring and
maintaining N copies. The launch is isolated behind `speckit_launch.py` and the kit's
`CommandRunner` (mockable; tests never hit the network). After the launch the produced layout is
**verified**; if spec-kit is unavailable, the command fails, or the layout is missing, the install
**fails fast** with an actionable message and leaves no partial state.

### Install-time dependency on spec-kit (Principle II derogation, declared)

The launch-installer pivot reintroduces a **fetch at install time** of spec-kit (inverting the
offline property of the old vendored bundle). This is a **declared derogation** of Principle II
(local-first), tracked in `specs/045-distribuzione-copilot-flow/plan.md` (Complexity Tracking):
governance is not a RAG capability (II targets the LLM/vector providers); the fetch is **pinned**,
deterministic, **fail-fast**, and behind a `CommandRunner` boundary.

## What is Sertor-authored vs. obtained via launch

| Surface | Origin | Claude container | Copilot container |
|---|---|---|---|
| SpecKit commands/agents + `.specify/**` | **launch** (`specify init`) | `.claude/**` + `.specify/**` | `.github/prompts/`+`.github/agents/` + `.specify/**` |
| `requirements-analyst`, `configuration-manager` | Sertor-authored (rendered) | `.claude/agents/*.md` | `.github/agents/*.agent.md` |
| skill `requirements` | Sertor-authored (rendered) | `.claude/skills/requirements/**` | `.github/prompts/requirements.prompt.md` |
| SDLC ritual block | Sertor-authored | `CLAUDE.md` (marker `SERTOR:SDLC-RITUAL`) | `.github/copilot-instructions.md` |
| constitution-starter | assistant-agnostic | `.specify/memory/constitution.md` | identical |

The Sertor-authored Copilot artifacts are **derived** from the single canonical Claude source via the
shared renderer in `sertor-install-kit` (anti-drift): only the container (frontmatter/path) is
translated, never the body.

## Invariants

install ≠ run · non-destructive · idempotent (re-run → skip) · fail-fast on spec-kit unavailable ·
gaps declared in the report (never silently omitted) · **no dependency on `sertor-core`**.
