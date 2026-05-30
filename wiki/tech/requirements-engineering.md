---
title: Requirements Engineering — Fase a Monte del Design
type: tech
tags:
  - requirements
  - methodology
  - ears
  - discipline
created: 2026-05-30
updated: 2026-05-30
sources:
  - EARS (Alistair Mavin)
  - Research session 2026-05-30
---

# Requirements Engineering — Fase a Monte del Design

Fase **autonoma e agnostica** di elicitazione, analisi e formalizzazione dei requisiti,
indipendente da qualunque framework di design a valle (es. SpecKit, phase-gate).

## Motivazione

Una ricerca approfondita (sessione corrente) ha confermato che i framework spec-driven
(SpecKit, IEEE 830, etc.) **non coprono bene** la fase di **requirements engineering a monte**:
- Spesso saltano direttamente da problem statement a specifica di design.
- Mancano di metodologia strutturata per elicitare criteri misurabili, vincoli, stakeholder,
  rischi, prioritizzazione.
- Non forniscono uno standard per formalizzare i requisiti atomici e testabili.

Abbiamo deciso di costruire una **fase nostra**, agnostica e riusabile, che serve come
**ponte consapevole** tra il problema (descritto dall'utente/stakeholder) e la specifica
di design (alimentata dai requisiti). La specifica a valle può leggere la cartella
`requirements/<short-name>/` senza dover conoscere se il backing framework è SpecKit,
IEEE 830, o altro.

## Formato output

Ogni requisito project vive in cartella `requirements/<short-name>/` (es. `requirements/sertor-rag/`).

**File principale:** `requirements.md` con sezioni:

1. **Contesto & Problema** — chi, cosa, perché; problema dichiarato.
2. **Obiettivi & Criteri di Successo** — misurabile (SMART).
3. **Stakeholder & Ruoli** — chi è influenzato; chi decide; chi esegue.
4. **Ambito (In/Fuori)** — esplicito boundary.
5. **Requisiti Funzionali** — cosa il sistema DEVE fare (metodologia **EARS**, vedi sotto).
6. **Requisiti Non-Funzionali** — performance, security, reliability, maintainability, scalability, cost.
7. **Vincoli, Assunzioni, Dipendenze** — hard limits; supposizioni; predecessori.
8. **Rischi** — failure modes, mitigazioni.
9. **Prioritizzazione MoSCoW** — Must, Should, Could, Won't.
10. **Domande Aperte** — ciò che NON è chiaro; servono clarifications.

## Metodologia EARS (Easy Approach to Requirements Syntax)

**EARS** è una metodologia pubblica e indipendente di Alistair Mavin per scrivere requisiti
testabili. Non è prescrivere **COSA** (è generico), bensì **COME formarlo**.

### 5 Pattern Fondamentali + Complex

Ogni requisito ha un ID `REQ-NNN` e segue uno di questi pattern:

1. **Ubiquitous (U):** "The system SHALL ALWAYS <action>"
   - Esempi: "REQ-001: The retriever SHALL ALWAYS return top-k results sorted by score."

2. **State-driven (S):** "WHEN <condition>, the system SHALL <action>"
   - Esempi: "REQ-002: WHEN embedding model changes, the index SHALL be invalidated."

3. **Event-driven (E):** "IF <event>, THEN the system SHALL <action>"
   - Esempi: "REQ-003: IF a user query arrives, THEN the orchestrator SHALL route to appropriate tool."

4. **Optional feature (O):** "The system MAY <action> IF <condition>"
   - Esempi: "REQ-004: The system MAY cache embeddings IF RAG_BACKEND=azure."

5. **Unwanted behaviour (UB):** "The system SHALL NOT <action> IF <condition>"
   - Esempi: "REQ-005: The system SHALL NOT expose API keys in logs."

6. **Complex (C):** combinazione di pattern; descrizione libera con ID atomico.

### Proprietà EARS

- **Atomico:** un'affermazione per requisito → testabile isolato.
- **Unambiguo:** "SHALL", "MAY", "SHALL NOT" → intento chiaro.
- **Tracciabile:** ID REQ-NNN → linkabile nel codice, design doc, test.
- **Formale ma leggibile:** non pseudo-codice, linguaggio naturale strutturato.

### Collegamento ai Test & Design

Ogni REQ-NNN ha una colonna "Test Plan":
- Come verificare che il requisito è soddisfatto.
- Unit test, integration test, acceptance test, manual check.

Design a valle **traccia i test ai REQ** → testabilità garantita per costruzione.

## Assets nel Workspace

### Skill (interattivo, workflow principale)

`.claude/skills/requirements/SKILL.md` — **workflow interattivo** che può fare domande
all'utente nel flusso principale:
- Guida step-by-step per elidere un progetto.
- Invita l'utente a popolare sezioni; domanda chiarificanti inline.
- Output: bozza di `requirements/<short-name>/requirements.md`.

### Subagent (delegabile, non interattivo)

`.claude/agents/requirements-analyst.md` — **subagent delegabile** (Sonnet, non interattivo):
- Prende in input problemi/brief lordi (anche mail, note, issue GH).
- Esegue analisi profonda: elicitazione, research, cross-talk simulato tra stakeholder.
- Output: **report** con sezioni EARS, domande aperte come `[DA CHIARIRE]` + tabella opzioni.
- Ha accesso a **tool MCP sertor-rag** per ancorare i requisiti al codebase reale
  (dogfooding: se i requisiti riguardano Sertor, l'agente ispeziona il codice).

## Principio di Disaccoppiamento

**Non riscrivere** le pagine di SpecKit (es. `tech/speckit.md`) per dire che
requirements engineering "fa parte di SpecKit" o è "una fase di SpecKit".

Invece: **requirements engineering è una disciplina autonoma** che pre-esiste
a qualunque orchestrazione a valle. SpecKit (come qualunque altro framework) può
consumare `requirements/<short-name>/` senza accoppiamento.

Eventualmente: aggiungere una **nota in SpecKit** che rimanda a questa pagina:
> "Fasi a monte (Constitution → Specify → Clarify) assumono che requisiti siano
> già stati elicitati. Per elicitazione strutturata, vedi [[requirements-engineering]]."

## Possibile estensione: tassonomia di dominio

Ogni progetto può aggiungere colonne custom ai requisiti EARS:
- `category` — funzionalità, infra, UX, API, etc.
- `owner` — chi è responsabile.
- `estimated_effort` — story points o ore (opzionale a questo stage).
- `acceptance_criteria` — link ai test su cui il design è verificato.

Tutto rimanendo coerente con il pattern EARS atomico.

## Link

- [[ears-methodology]] — approfondimento su EARS e best practice.
- [[speckit]] — framework di governance a valle (consuma requisiti).
