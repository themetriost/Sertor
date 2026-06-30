# Checklist di qualità — Specifica `082-parity-guard-budget`

Validazione della `spec.md` (E10-FEAT-024 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive le due lacune reali (parity guard che esclude `.ps1`/JSON + assenza di assert di presenza eventi nel wiring Copilot; nessun freno alla ricrescita dei blocchi always-on) e il valore («CI rossa quando un evento sparisce o un blocco supera la soglia», igiene del contesto reso all'agente ospite). I requisiti parlano di esiti osservabili (guardia rossa, messaggio nominante), non di codice dei test specifico.
- [x] **C2** Nessun dettaglio implementativo prescrittivo nei requisiti. **PASS** — collocazione dei nuovi test (file dedicato vs estensione), root vs package, regex di strip commenti sono confinati nelle «Forche di design» (DA-D-1/2/3). Le decisioni di prodotto (soglie 60/58/70, Gruppo C come Should) sono codificate come scelte fissate, non come prescrizioni di edit.
- [x] **C3** I riferimenti a file/simboli ancorano, non prescrivono il come. **PASS** — riquadro «Ancoraggio all'esistente»: i 6 frammenti del wiring (`render_copilot_hooks`/`_rag_hook_fragment`), i pattern da riusare (`test_schema_copilot_hooks.py` tmp_path, `test_assets_hook_breadcrumb.py` anti-vacuità, `test_assets_hook_cli_invocation.py` strip commenti) e i conteggi reali (52/49/64) ancorano i requisiti allo stato verificato.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..013 hanno esito osservabile (presenza eventi nel JSON / fallimento nominante / anti-vacuità / complementa schema / budget per-blocco con soglie 60/58/70 / coverage esaustiva / messaggio diagnostico / costanti esplicite / no payload stdout / strip commenti / offline / non-regressione suite).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US6 (frammento rimosso→rosso, blocco oltre soglia→rosso, nuovo blocco non registrato→rosso, FEAT-049 coperto, no payload stdout rag, suite verdi+offline) hanno ciascuna Independent Test e acceptance G/W/T.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — trailing newline (FR-008/A-004), nuovo frammento Copilot (R-1/A-003), governance senza hook JSON (A-002), prosa nei commenti rag (FR-010), quarto blocco non registrato (FR-006).

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (rimozione frammento→test rosso nominante, anti-pattern incluso), CS-2 (blocco sopra soglia→file+conteggio+soglia; blocco non registrato→rosso; fixture sintetica), CS-3 (FEAT-049→schema-test rosso, presenza indipendente), CS-4 (zero nuovi fallimenti `uv run pytest`), CS-5 (offline, no rete/uv/pwsh).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (guardia rossa/verde, conteggio+soglia, suite verde, offline), non di scelte implementative dei test; i riferimenti `uv run pytest`/`tmp_path` sono criteri di accettazione meccanici osservabili.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (event-presence guard diventa rossa rimuovendo un frammento) e CS-2 (budget guard diventa rossa sopra soglia) sono la prova diretta del valore: le due falle di ISSUE-10 ora producono una CI rossa.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..5 della spec mappano CS-1..5 dei requirements; coprono FR-001..013 (REQ-001..017 + NFR-1..6), incluse le decisioni fissate DA-1 (soglie differenziate) e DA-2 (Gruppo C Should).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: Gruppo A (shape-guard presenza Copilot), Gruppo B (budget cross-package), Gruppo C (source-level guard rag stdout, Should), non-regressione+offline. Fuori: core, codice runtime invariato, parity-guard di contenuto su `.ps1`/`.json`, esecuzione pwsh reale, `.vscode/`/VS Code, sync `assets/rag` ↔ `.claude`, guard auto-aggiorna-soglia, fork IT eval (FEAT-025), il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — l'unico rinvio reale (riconciliazione fork IT eval-skill) è promosso a **FEAT-025** nel backlog d'epica; gli altri «fuori ambito» sono confini di scope o questioni di plan, non capacità future sepolte.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — wiring Copilot rag (6 frammenti), shape-guard di presenza (nuova), blocchi always-on (52/49/64), budget-test (nuovo, soglie 60/58/70), source-level guard rag (nuova, Should), guardie esistenti (verdi/invariate).

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: wiring Copilot con un evento mancante e blocchi always-on che ricrescono degradano il contesto reso all'agente ospite (freschezza non enforced; segnale-rumore dell'istruzione always-on); le guardie sono igiene host-facing sul confine D↔N, nessun core/LLM/cambiamento di comportamento.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVA / solo test e guardie, ZERO codice di `sertor_core`», idealmente zero codice runtime; generazione payload byte-identica prima/dopo per entrambi gli assistenti.
- [x] **C16** Principi riflessi: X (host-agnostico, generazione invariata), XI (zero `sertor_core`, nessun runtime toccato), additività/non-regressione. **PASS** — RNF-1 (zero core), RNF-2 (comportamento installer byte-identico), FR-013 (additività e non-regressione suite), FR-012 (offline-safe).

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese sono codificate come **RISOLTE**. **PASS** — DA-1 marcata FISSATA: soglie differenziate wiki=60/RAG=58/SDLC=70 (con motivazione esplicita: 75 uniforme lascerebbe ricrescere oltre i pre-FEAT-021 71/72), tradotta in FR-005/008; DA-2 marcata FISSATA: Gruppo C IN AMBITO come SHOULD (FR-009/010/011), non declassata a Could.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-1 collocazione shape-guard, DA-D-2 collocazione budget-test, DA-D-3 forma source-level guard) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le due forche di scope dei requirements (DA-1 soglia budget, DA-2 ambito source-level guard) sono **risolte**
con decisioni vincolanti del flusso principale (soglie differenziate 60/58/70; Gruppo C come Should). Le
forche residue DA-D-1/2/3 sono questioni di *come* (collocazione/forma dei test), risolvibili in plan.
Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
