# Checklist di qualità — Specifica `080-pulizia-stile-skill`

Validazione della `spec.md` (E10-FEAT-022 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (ALL-CAPS pervasivo, sezioni ridondanti, file 282 righe senza ToC, wikilink orfano che non risolve sull'ospite) e il valore «asset più leggibili/manutenibili per agente, manutentore e auditor, senza cambiare il comportamento»; i requisiti parlano di leggibilità/dedup/navigabilità/host-agnosticità, non di sintassi di edit dei `.md`.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — il criterio operativo ALL-CAPS, la forma esatta della ToC/anchor, la forma della riscrittura del wikilink, la regola di condensazione e la forma della guardia sono confinati a «Forche di design» (DA-D-1..5) e «Fuori ambito»; le decisioni di scope (DA-1/2/3) sono codificate come scelte di prodotto fissate con l'utente, non come prescrizione di codice.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: l'inventario degli asset (path + righe), `sertor-cli-reference.md` (FEAT-021) e le guardie `test_assets_sync.py`/`test_assets_copilot_guard.py` ancorano i requisiti agli asset/meccanismi reali, non impongono il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..015 hanno esito osservabile (ALL-CAPS normalizzato / *why* preservato / acronimi-codice esclusi / una proibizione un posto / regole uniche conservate / sezione svuotata chiusa / ToC navigabile / wikilink orfano rimosso / riscrittura self-contained / pointer al reference unico / host-agnostico / nessun cambiamento semantico / sync dogfood↔bundle / guardia anti-regressione / lifecycle additivo).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US9 (no ALL-CAPS, una proibizione un posto, ToC navigabile, nessun wikilink orfano, «How to invoke» una sola fonte, nessun cambiamento di comportamento, parità host-agnostica, dogfood in sync, guardia anti-regressione) hanno ciascuna Independent Test e acceptance G/W/T.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — ALL-CAPS legittimo, ALL-CAPS che accompagna una regola, regola presente solo in «What NOT to do», sezione svuotata, wikilink rimosso ma frase monca, altri wikilink orfani, pointer morto, `requirements/SKILL.md` in italiano (solo stile), drift dogfood↔bundle, reintroduzione di un sintomo.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (grep ALL-CAPS = 0 sui file in scope), CS-2 (zero regole duplicate inline↔sezione sui casi noti), CS-3 (ToC presente con ≥8 titoli + lista anchor in testa), CS-4 (grep `[[` senza match orfani), CS-5 (parità Copilot verde + confronto prima/dopo senza diff semantico), CS-6 (byte-parità dogfood dopo sync, guardia verde).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (zero ALL-CAPS, zero duplicazioni, ToC presente, zero wikilink orfani, nessun cambiamento semantico, sync byte-identico), non di tool di edit o struttura interna degli asset; le verifiche grep sono criteri di accettazione meccanici, non prescrizioni d'implementazione.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (ALL-CAPS eliminato) + CS-3 (ToC navigabile) + CS-4 (zero wikilink orfani) + CS-5 (nessun cambiamento semantico) sono la prova diretta del valore «asset più leggibili, senza cambiare comportamento».
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..6 della spec mappano CS-1..6 dei requirements; coprono FR-001..015 (REQ-001..012 + Could §9) e i quattro sintomi (ALL-CAPS, dedup, ToC, wikilink orfano) + obiettivo «How to invoke una fonte».

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: 5 file skill (`guided-setup`, `eval-suite-author`, `eval-feedback`, `wiki-playbook`, `requirements/SKILL.md`), pointer eval-skills, ToC, fix wikilink, sync `.claude/` + guardie. Fuori: core, agenti distribuiti, blocchi `CLAUDE.md` (FEAT-021), `sertor-cli-reference.md`, `wiki-author/SKILL.md`, traduzione lingua (E12), budget altitude (FEAT-024), stub Copilot (FEAT-023), il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: budget altitude → FEAT-024; stub/onestà surface Copilot → FEAT-023; traduzione lingua → E12; pulizia agenti distribuiti → intervento autonomo separato. Nessun rinvio reale sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — asset skill in scope (inventariati), riferimento unico CLI (`sertor-cli-reference.md`), Table of Contents, wikilink orfano, copie dogfood, guardia anti-regressione.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: le skill sono contesto operativo reso all'agente; una skill con ALL-CAPS incongruenti, regole duplicate e wikilink orfano è contesto rumoroso/fuorviante; ripulirla preservando ogni istruzione load-bearing rafforza la qualità del contesto; D↔N (solo forma/leggibilità host-facing, nessun core, nessun LLM); complementa FEAT-021 e lascia il freno a FEAT-024.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVA / igiene host-facing, ZERO codice di core»: solo asset `.md` + guardie; modifica puramente di forma; zero cambiamento di comportamento/semantica; un agente riceve le stesse istruzioni operative in forma più leggibile.
- [x] **C16** Principi riflessi: X (host-agnostico, body byte-identici Claude↔Copilot), XI (vehicle-only, zero `sertor_core`, niente LLM), igiene-leggibilità senza regressione semantica. **PASS** — FR-011/RNF-2, RNF-1/RNF-5, FR-012/RNF-3; coerenza con FEAT-021 (RNF-5) e cross-ref a FEAT-023/024/E12.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-1 (eval-skills «How to invoke» → pointer closure-safe, in ambito), DA-2 (ALL-CAPS anche su `requirements/SKILL.md`, solo stile, lingua invariata), DA-3 (wikilink orfano → host-agnostico, niente riferimento al wiki interno) marcate FISSATE nel riquadro decisioni e tradotte in FR-001/010 e FR-008/009.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-1 criterio ALL-CAPS, DA-D-2 forma ToC, DA-D-3 forma riscrittura wikilink, DA-D-4 forma guardia, DA-D-5 regola di condensazione) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le due forche di scope aperte nei requirements (§10 — «How to invoke» eval-skills; `requirements/SKILL.md`
in italiano) sono entrambe **risolte** con decisioni vincolanti dell'utente (DA-1: in ambito, pointer;
DA-2: solo stile, lingua invariata), più il fix wikilink (DA-3). Le forche residue DA-D-1..5 sono
questioni di *come* (criterio ALL-CAPS, forma ToC/anchor, riscrittura wikilink, forma guardia, regola di
condensazione), risolvibili in plan. Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non
necessaria).
