# Checklist di qualità — Specifica `078-portabilita-os-hook`

Validazione della `spec.md` (E10-FEAT-018 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (hook `.ps1` invocati con `"shell": "powershell"` → su mac/Linux non partono mai, silent exit 0; claim implicito di parità che nasconde surface inerti su Copilot) e il valore «l'installer dichiara onestamente cosa non funzionerà + rimediazione azionabile»; i requisiti parlano di rilevamento prerequisito, note nel report, documentazione, non di sintassi Python/PowerShell.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — la collocazione del check (singoli builder vs. helper kit), la forma esatta delle note, l'aggiornamento della tabella capability e l'emissione condizionale della nota Copilot sono confinati a Forche di design (DA-D-r1/r2) e Fuori ambito; l'uso di `InstallReport.notes` è una scelta di prodotto fissata con l'utente (riusare il meccanismo esistente), non una prescrizione di codice.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: `"shell": "powershell"` (wiring Claude), `_PWSH = "pwsh -File"` (wiring Copilot), `InstallReport.notes`/`.note()`, `test_claude_report_has_no_gap_note`, breadcrumb FEAT-019 — accertati e usati per ancorare i requisiti agli asset/meccanismi reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..015 hanno esito osservabile (rileva pwsh su non-Windows / nota con surface+URL / nota in resa umana e JSON / nessuna nota se pwsh presente / check non-fatale / nessuna nota su Windows / nota memory-capture Copilot / cross-ref capacità pianificata / nessuna nota Copilot su Claude+Windows / docs install.md prerequisito / docs install-copilot.md / docs surface per target / guardia note pwsh / guardia nota Copilot / sync dogfood↔bundle).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US7 (gap pwsh dichiarato, nessun falso allarme con pwsh, non-regressione Claude+Windows, install non bloccato, onestà memory-capture Copilot, documentazione utente, guard tests + sync).
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — host non-Windows senza/con pwsh, Windows+Claude invariato, install Copilot rag (nota anche con SERTOR_MEMORY spento), check binario senza OS-detection sofisticata, falso positivo su Windows, rilevamento runtime escluso, nota memory-capture che diventa stale, CI su Windows con OS mocking.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (simula assenza pwsh → ispeziona report.notes), CS-2 (simula presenza pwsh → nota assente), CS-3 (test esistente report.notes == []), CS-4 (ispeziona report.notes su install Copilot simulato), CS-5 (leggi i due file docs), CS-6 (esegui la suite di guardia con OS mocking + sync verde).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (nota dichiarata/assente, non-fatalità, report pulito su Windows, configurazione richiesta dichiarata, prerequisito documentato, guardie verdi), non di API Python specifiche, sintassi PowerShell o struttura interna degli asset.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (gap pwsh dichiarato invece che nascosto) + CS-4 (onestà su memory-capture Copilot) sono la prova diretta dei due valori della feature (portabilità onesta + claim veritieri).
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..6 della spec mappano CS-1..5 dei requirements (con CS-6 della spec che esplicita le guardie REQ-013/014/015); coprono REQ-001..015 (FR-001..015) e i due obiettivi (guardia pwsh + onestà surface).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: rilevamento pwsh install-time (rag+wiki, non-Windows), nota indisponibilità pwsh, nota memory-capture Copilot, documentazione utente (install.md + install-copilot.md), guard tests + sync. Fuori: gemello bash, guardia pwsh su Windows (FEAT-019), rilevamento runtime, codice core, distribuzione SERTOR_MEMORY_ADAPTER (FEAT-009 memorie), visibilità SessionStart Copilot (E10-FEAT-008), pulizia stile (FEAT-021/022), il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: distribuzione SERTOR_MEMORY_ADAPTER → FEAT-009 memorie; visibilità SessionStart Copilot → E10-FEAT-008; pulizia stile/altitude → FEAT-021/022; gemello bash + guardia pwsh runtime → Won't per decisione utente. Nessun rinvio reale sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — nota indisponibilità pwsh, nota inertness memory-capture Copilot, meccanismo InstallReport.notes, guardia pwsh install-time, surface hook depositati ma non-operativi, documentazione utente toccata.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: un installer che dichiara operativi hook che su mac/Linux non partono mai è il modo in cui l'apparato si scopre rotto solo settimane dopo (dogfooding cieco esteso all'ospite); rendere la portabilità onesta protegge la stella polare; D↔N (rilevamento+note meccanici senza LLM; azione sui gap all'agente/utente); complementa FEAT-019.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO + host-facing, ZERO codice di core»: solo pacchetto installer + docs utente + test di guardia; zero `sertor_core`; a comportamento sano (Windows+Claude o non-Windows con pwsh) funzionamento invariato (report.notes == []).
- [x] **C16** Principi riflessi: X (host-agnostico, portabilità reale, check binario senza hardcoding distro), XI (vehicle-only, no `sertor_core`, no LLM nel check), XII (fail-loud — nota azionabile invece di silent exit 0; claim veritieri), VI (non-regressione Claude+Windows). **PASS** — FR-001/RNF-4, RNF-2/RNF-7, FR-002/007/RNF-1, FR-006/009/RNF-5.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-1 (strategia = guardia pwsh + gap dichiarato, hook PS-only senza bash), DA-2 (onestà surface via InstallReport.notes), DA-3 (memory-capture Copilot = nota; distribuzione adapter = FEAT-009), DA-4 (SessionStart Copilot funzionale, non inerte → E10-FEAT-008) marcate RISOLTE; nessuna riapertura.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-r1 collocazione del check pwsh; DA-D-r2 nota memory-capture sempre vs. condizionata + tabella capability), che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le decisioni di scope (strategia OS = guardia pwsh + gap dichiarato; onestà surface via
`InstallReport.notes`; memory-capture Copilot = nota con cross-ref; SessionStart Copilot fuori ambito)
sono risolte con decisioni vincolanti dell'utente e verifica codice, codificate come fissate (DA-1..4).
Le forche residue DA-D-r1/r2 sono questioni di *come* (collocazione del check; emissione condizionale
della nota Copilot; tabella capability), risolvibili in plan. Non sono emerse ambiguità genuinamente
nuove. Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
