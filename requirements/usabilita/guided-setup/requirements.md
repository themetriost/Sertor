# Requisiti — guided-setup (guida agentica a install → configure → verify)
<!-- Deriva da: FEAT-002 (epica usabilità) -->

## 1. Contesto e problema (perché)

Il primo contatto è oggi il momento più fragile: l'utente deve sapere quale comando lanciare, scegliere
il provider, riempire `.sertor/.env` **a mano**, gestire il download GloVe e capire se "ha funzionato".
Gli errori si auto-spiegano ma **uno alla volta**, e non c'è un percorso che li **anticipi**.

`guided-setup` è la prima feature **agentica** dell'epica: una **skill** (più un ramo dell'agente
*concierge*) che l'**agente frontier dell'ospite** esegue per condurre l'utente da "repo non
configurato" a "**RAG verificato**" — *conversando*, scegliendo il provider dal contesto e
**orchestrando solo i vehicle deterministici** (`sertor install`, `sertor configure --set`,
`sertor-rag doctor`). Coerente col confine **D↔N**: l'intelligenza è nell'agente ospite, **il core non
chiama mai un LLM**.

## 2. Obiettivi e criteri di successo
- **CS-1:** un utente arriva da nulla a **`doctor` "tutto verde"** seguendo la guida, **senza** conoscere
  gli internals (né i nomi dei comandi/knob).
- **CS-2:** la skill **sceglie il provider dal contesto** (airgapped? credenziali cloud presenti?
  esigenza di semantica NL?) e lo **motiva**, lasciando la decisione finale all'utente.
- **CS-3:** i segreti sono inseriti via i vehicle (`configure --set`/`getpass`) e **mai stampati**.
- **CS-4:** al termine la skill lancia **`sertor-rag doctor`** e riporta l'esito **verificato** —
  *fail-loud* se non è verde (Principio XII), niente "fatto" presunto.
- **CS-5:** la skill è **host-agnostica** e installabile su **Claude e Copilot** col pattern di
  distribuzione esistente (guardia di parità).

## 3. Stakeholder e attori
- **Utente nuovo:** il beneficiario diretto (vuole "funziona" senza studiare Sertor).
- **Agente frontier dell'ospite:** l'**esecutore** della skill (orchestra i vehicle, conversa).
- **Vehicle deterministici:** `sertor install`, `sertor configure`, `sertor-rag doctor`/`index` — gli
  strumenti che la skill richiama (non li reimplementa).
- **Agente *concierge* (FEAT-009):** ospiterà guided-setup come uno dei suoi rami.

## 4. Ambito

### In ambito
- Una **skill** (asset host-agnostico) che prescrive il flusso **install → configure → verify**
  conversando, e il relativo **ramo dell'agente concierge**.
- **Scelta guidata del provider** dal contesto del repo + spiegazione (rimanda a config-recommender,
  FEAT-004, quando esisterà; per ora sceglie con euristica semplice + conferma utente).
- **Compilazione di `.env`** via `sertor configure --set`/prompt sicuri (mai a mano, mai segreti a
  schermo).
- **Gestione dell'attesa del download GloVe** (annuncia cosa accade; si appoggia al progress di FEAT-003
  quando disponibile).
- **Verifica finale** via `sertor-rag doctor` (FEAT-001) con esito onesto.
- **Distribuzione dual-target** (Claude `.claude/skills` ↔ Copilot `.github/skills`) via `sertor install`.

### Fuori ambito
- I **comandi deterministici** in sé (`install`/`configure`/`doctor`): esistono o sono FEAT-001 — la
  skill li **usa**, non li ricrea.
- **Auto-installazione senza consenso:** la skill propone ed esegue **su conferma**, non agisce di
  nascosto.
- **Il core che chiama un LLM** (D↔N): l'intelligenza è nell'agente ospite.
- La **raccomandazione di config approfondita** (profilazione ricca del repo): è FEAT-004
  (config-recommender); qui basta un'euristica semplice.

## 5. Requisiti funzionali (EARS)
> Soggetto = la **skill di usabilità** (eseguita dall'agente ospite) e il sistema di asset attorno.
- **REQ-001 (Event-driven):** *When the user asks to set up Sertor, the guided-setup skill shall walk
  the user through install → configure → verify using only the deterministic vehicles.*
- **REQ-002 (Optional):** *Where cloud embedding credentials are absent (or the host is airgapped), the
  skill shall recommend a local provider (`glove`/`hash`) and explain the trade-off, leaving the choice
  to the user.*
- **REQ-003 (Event-driven):** *When a configuration secret is needed, the skill shall set it via
  `sertor configure --set`/secure prompt and shall never print the secret value.*
- **REQ-004 (Event-driven):** *When the GloVe provider is chosen and not cached, the skill shall inform
  the user of the one-time download before triggering the first index.*
- **REQ-005 (Event-driven):** *When setup steps complete, the skill shall run `sertor-rag doctor` and
  report the verified status.*
- **REQ-006 (Unwanted):** *If `doctor` is not all-green, then the skill shall surface the failing area
  and the remediation, and shall not declare setup successful (fail loud, Principio XII).*
- **REQ-007 (Ubiquitous):** *The skill shall be host-agnostic and installable on both supported
  assistants via the existing installer, covered by the parity guard.*
- **REQ-008 (Unwanted):** *If a step would change the host without consent, then the skill shall ask for
  confirmation before executing it.*
- **REQ-009 (State-driven):** *While re-run on an already-configured host, the skill shall be idempotent
  (detect existing config and verify, not blindly re-scaffold).*

## 6. Requisiti non funzionali
- **NFR-1 (D↔N, Principio XI):** la skill è eseguita dall'agente ospite e usa solo i vehicle; il core
  non chiama un LLM.
- **NFR-2 (host-agnostico, Principio X):** corpo della skill byte-identico tra Claude e Copilot
  (riferimento per nome agli asset, come `wiki-author`); contenitore tradotto nativamente.
- **NFR-3 (privacy):** nessun segreto a schermo/nei log; i segreti passano per i percorsi sicuri del
  wizard.
- **NFR-4 (onestà):** lo stato riportato è quello **verificato** da `doctor`, non presunto.

## 7. Vincoli, assunzioni e dipendenze
- **Dipendenza forte da FEAT-001 (`sertor-rag doctor`):** è il passo di *verify*; senza, la skill
  resterebbe cieca sull'esito → FEAT-001 è prerequisito.
- **Dipendenza da E2 `sertor-cli`:** `sertor install` e `sertor configure` (wizard, `--set`) sono i
  vehicle orchestrati.
- **Sinergia con FEAT-003 (progress GloVe)** e **FEAT-004 (config-recommender):** li usa quando
  esistono; degrada a euristica/annuncio semplice finché non ci sono.
- **Riuso del pattern di distribuzione** dual-target esistente (skill/agenti via `sertor install`,
  render da fonte unica, guardia di parità).
- **Assunzione:** l'agente frontier è disponibile sull'ospite (presupposto del modello agentico).

## 8. Rischi
- **R-1 — Dipendenza da `doctor` non ancora pronto:** mitigare consegnando **FEAT-001 prima** (MVP =
  doctor → guided-setup).
- **R-2 — Azioni non consensuali:** una skill che "fa troppo" sull'ospite. Mitigare con REQ-008
  (conferma) e idempotenza (REQ-009).
- **R-3 — Drift dual-target:** corpo che diverge tra Claude/Copilot. Mitigare con la guardia di parità
  esistente (riferimento-per-nome, body neutro).
- **R-4 — Euristica provider troppo semplice:** rischio di consigli mediocri finché manca FEAT-004.
  Accettabile per l'MVP (l'utente conferma); FEAT-004 lo raffina.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001/003/005/006/007 (flusso guidato, segreti sicuri, verify via doctor + fail-loud,
  installabile dual-target).
- **Should:** REQ-002 (scelta provider dal contesto), REQ-004 (annuncio GloVe), REQ-008 (consenso),
  REQ-009 (idempotenza).
- **Could:** integrazione con config-recommender (FEAT-004) e progress GloVe (FEAT-003) appena pronti.

## 10. Domande aperte
- **DA-G1 — Skill autonoma vs ramo del concierge:** [DA CHIARIRE: guided-setup nasce come skill
  invocabile a sé **e** come ramo dell'agente concierge (FEAT-009)? Default proposto: skill a sé
  (testabile/invocabile da sola), che il concierge poi dispatcha.]
- **DA-G2 — Profondità dell'euristica di scelta provider:** [DA CHIARIRE: quanto deve "profilare" il
  repo prima di FEAT-004? Default proposto: minimo (creds presenti? airgapped?) + conferma utente,
  rimandando la profilazione ricca a FEAT-004.]
- **DA-G3 — Confine d'esecuzione sull'ospite:** [DA CHIARIRE in design: quali passi la skill esegue
  direttamente (via i vehicle) e quali solo propone — soprattutto `uv`/install. Default proposto:
  propone+esegue-su-conferma per install/configure; esegue liberamente i check di sola lettura.]
