# Checklist di qualità — Specifica `077-version-update-check`

Validazione della `spec.md` (E2-FEAT-013 epica sertor-cli). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (`git+url` + cache `uvx` → ospite silenziosamente stantio, nessun segnale automatico oggi) e il valore «l'ospite scopre da solo di essere indietro, l'utente decide»; i requisiti parlano di check/avviso/cache/persistenza/distribuzione, non di codice.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — URL esatto del `/VERSION` remoto, nome/formato del file di stato, sorgente della versione installata, chi esegue la GET su Copilot, fusione vs separazione dall'hook di freschezza, semantica del confronto — tutti confinati a «Forche di design» (DA-1..DA-5) e «Fuori ambito»; `.sertor/.version-check.json` marcato «es.».
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: `/VERSION` (fonte unica letta dai `pyproject`), meccanismo installer hook (FEAT-011 `rag-freshness*` + `install_rag.py`), seam `AssistantProfile`, `RUNTIME_IGNORES` — accertati e usati per ancorare i requisiti ai meccanismi reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..018 hanno esito osservabile (check all'avvio / ultima da `/VERSION` / avviso quando indietro / nessun avviso allineato / mai auto-upgrade / cache ~1/giorno / stato persistito / re-check forzato / offline skip / indeterminato skip / copertura 3 dimensioni / nomina dimensione indietro / loop chiusa / no LLM no core / no segreti in rete / deposito parità / lifecycle / `.gitignore`).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US9 (scoperta all'avvio, determinazione da `/VERSION`, ~1 rete/giorno, offline non-fatale, stato sotto `.sertor/`, 3 dimensioni, loop chiusa, parità installer, re-check forzato).
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — offline/lookup fallito, `/VERSION` non parsabile, installato più nuovo, cache fresca, aggiornamento a metà giornata, più dimensioni a versioni diverse, una sola dimensione, Copilot prompt-statico, `pwsh` assente, bump raro, coesistenza con FEAT-011.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — CS-1 (avviso nomina i 3 campi se indietro, zero avviso se allineato), CS-2 (≤ ~1 rete/giorno, non bloccante, offline = no avviso/no errore), CS-3 (copre rag+wiki+governance da fonte unica), CS-4 (0 auto-upgrade), CS-5 (installabile Claude+Copilot con parità+lifecycle), CS-6 (no LLM/no `sertor_core`, solo GET `/VERSION` pubblico).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (avviso corretto, economicità, copertura, solo-avviso, installabilità con parità, privacy), non di linguaggio/SDK/struttura interna dell'asset.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (avviso corretto quando indietro / silenzio quando allineato) è la prova diretta del valore.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..6 della spec mappano CS-1..6 dei requisiti; gli FR-001..018 coprono REQ-001..018.

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: check cachato all'avvio (GET `/VERSION` + confronto), avviso non-invasivo, stato sotto `.sertor/`, degradazione non-fatale, distribuzione host-facing parità+lifecycle, voce `.gitignore`. Fuori: applicazione dell'aggiornamento, commit-SHA, PyPI, pulizia artefatti (FEAT-015), freschezza corpus (FEAT-011), il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: applicazione aggiornamento → `sertor upgrade`/FEAT-008; commit-SHA → eventuale nuova FEAT `sertor-cli` (non sepolta); pulizia artefatti → E10-FEAT-015; freschezza corpus → E10-FEAT-011; corollario «feature completa» reso esplicito (host-facing in ambito FR-016..018, non rinviato).
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — check di version-update (harness), stato persistito, verdetto di versione, `/VERSION` (fonte unica), avviso d'aggiornamento, voci/asset per-assistente.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: un ospite silenziosamente stantio è minaccia indiretta alla qualità del contesto reso all'agente; la feature serve adozione/portabilità (Principio X); D↔N (segnala, non aggiorna, no LLM); periferica al differenziatore ma abilitatrice.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO (harness + distribuzione), nessun codice di core»: raccomanda `sertor upgrade`/`uvx --refresh`, non li reimplementa né auto-aggiorna; a feature non installata comportamento invariato; corollario «feature completa».
- [x] **C16** Principi riflessi: X (host-agnostico, formato nativo per assistente), XI (no `sertor_core`), D↔N (segnala/induce, utente agisce, no LLM), privacy (solo GET `/VERSION` pubblico). **PASS** — FR-016/RNF-3, FR-014, FR-005/FR-014/RNF-5, FR-015/RNF-4.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **fissate**, non riaperte. **PASS** — (1) home epica E2, (2) «newer» = bump `/VERSION` su `master` non SHA, (3) cache ~1/giorno + stato in `.sertor/.version-check.json` + non-fatale offline exit 0, (4) solo avviso mai auto-upgrade: incorporate in FR/CS/Assumptions e ribadite in «Forche di design» come fissate.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-1 chi-esegue-su-Copilot, DA-2 URL `/VERSION` remoto, DA-3 sorgente installato, DA-4 fusione vs separazione hook, DA-5 semantica confronto) che non cambiano lo scope e si chiudono in clarify/plan.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. **Nessun `[NEEDS CLARIFICATION]` da girare
all'utente:** le quattro decisioni di scope sono già prese e codificate come fissate; le forche residue
DA-1..DA-5 sono questioni di *come* (chi esegue la GET su Copilot, URL del `/VERSION` remoto e sua
parametrizzazione, sorgente della versione installata, fusione vs separazione dall'hook di freschezza,
semantica del confronto), risolvibili in `/speckit-clarify` o `/speckit-plan`. Pronta per il passo
successivo.
