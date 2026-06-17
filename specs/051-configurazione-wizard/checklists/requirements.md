# Specification Quality Checklist: Configurazione guidata (wizard) — `sertor configure`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-17
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Le 4 decisioni di scope (Q1 modalità ibrida CI-safe; Q2 comando separato `sertor configure`
  ri-eseguibile; Q3 validazione statica + probe live opzionale; Q4 solo provider/store supportati dal
  core) sono **già risolte** a monte (requirements §10) e codificate nella spec → **nessun** marker di
  chiarimento.
- Terminologia tech-agnostica deliberata: «file di configurazione locale» (non `.sertor/.env`),
  «fusione additiva non distruttiva» (non `env_merge`), «validazione statica / fonte di verità di
  runtime» (non `Settings.validate_backend`), «controllo live (probe)», «terminale interattivo» (non
  TTY), «esito di successo/errore/uso errato» (non exit code 0/1/2). I nomi concreti — `sertor
  configure`, `.sertor/.env`, `Settings.validate_backend`, `env_merge`, le manopole
  `AZURE_OPENAI_*`/`AZURE_SEARCH_*`/`RAG_BACKEND`, `--check`/`--json`/`--overwrite`, gli adapter
  Chroma/Azure AI Search/Ollama — sono *come* di design e vivono nel requirements e nel piano, non nei
  Success Criteria.
- Il vincolo di realtà su provider/store (Q4): la spec offre solo embedding Azure OpenAI / Ollama e
  store Chroma / Azure AI Search, coerente con la sola fonte di verità di runtime (validazione di
  backend) verificata a monte (`local` mai bloccato; Azure embedding richiede endpoint/chiave/deployment
  di embedding; Azure store richiede endpoint/chiave di ricerca).
- Restano **domande di design → `/speckit-plan`** (presentazione opzioni/prompt; rilevamento del
  terminale interattivo; forma del probe live; nomi esatti di comando/opzioni e mappatura sugli exit
  code; sede/forma del report strutturato). Non sono ambiguità di *cosa/perché* e non bloccano la spec.
- `install ≠ run`, non distruttività, idempotenza e segreti-mai-versionati sono codificati come
  invarianti (FR-012/FR-014/FR-030, SC-003/SC-005/SC-008/SC-009), coerenti con l'epica e con le
  decisioni D4 di `lifecycle-installer`.
