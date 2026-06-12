# Epica — Collaborazione multiutente / enterprise (cosa condividere, cosa no, quando)
<!-- STATO: APERTA, DA AFFRONTARE IN SEGUITO (decisione utente, 2026-06-12). Epica trasversale:
     non è un tema di installer, è un tema di WORKFLOW collaborativo su RAG + Wiki. -->

> **Epica trasversale (workflow), non di prodotto-singolo.** Tocca core, CLI/installer e wiki insieme.
> Aperta su decisione dell'utente (2026-06-12) per **dare casa** al tema, ma **da affrontare più
> avanti**: ha molte sfumature che meritano una discussione approfondita prima di decomporre.

## 1. Visione e problema (perché)

Sertor punta a un uso **enterprise e multiutente**: più sviluppatori che lavorano sullo **stesso
repository** con il RAG e l'LLM Wiki installati. Oggi il modello è implicitamente **mono-utente**
(ognuno installa, indicizza e scrive in locale). Il salto a un uso di team apre un tema di
**workflow collaborativo** che va oltre "dove metto i file":

- **Cosa si condivide e cosa resta privato?** (config, indice, wiki, segreti, ambiente)
- **Quando si condivide?** (a ogni commit? su trigger? con quale cadenza? chi pubblica?)
- **Come collaborano più dev sullo stesso artefatto vivo?** (il wiki scritto a più mani; l'indice
  RAG ricostruito da chi e quando; i conflitti di merge sulla conoscenza)
- **Chi possiede/cura cosa?** (governance leggera: ruoli, responsabilità sul wiki e sugli indici)

Il problema è di **modello di collaborazione**, non solo di collocazione di file. Va disegnato con
cura perché tocca la natura "memoria viva" del wiki e "contesto sempre reale" del RAG quando i
contributori sono molti.

## 2. Ambito

### In ambito (dell'epica, da decomporre poi)
- **Modello di ownership** degli artefatti: matrice *team-condiviso (versionato) ↔ per-utente* per
  ogni artefatto prodotto da Sertor (config, indice, wiki, ambiente, segreti).
- **Modalità mono-utente ↔ team/enterprise** come driver dei default, e dove vive questa scelta.
- **Collaborazione sul RAG**: indice condiviso (store remoto) vs per-utente; quando/da chi si
  (ri)costruisce; coerenza del "contesto reale" tra dev.
- **Collaborazione sul Wiki**: più dev che scrivono/curano la stessa LLM Wiki; merge della
  conoscenza, cura, evitare deriva collettiva.
- **Quando condividere**: cadenze/trigger di pubblicazione (commit, push, rebuild), e cosa è
  automatico vs manuale.
- **Segreti e config per-utente**: credenziali mai versionate, ognuno il suo `.env`/ambiente.

### Fuori ambito (dell'epica)
- **Dove** stanno i file sull'ospite (collocazione/igiene radice) → è la feature
  [`igiene-radice-host`](../sertor-cli/igiene-radice-host/requirements.md) di `sertor-cli` (asse
  ortogonale, indipendente da questo tema).
- **Implementazione** di nuovi adapter store (MongoDB/PGVector) → capacità del core
  (`sertor-core`), qui se ne definisce semmai l'uso collaborativo.
- **Vault/SSO/segreti centralizzati** di livello enterprise (oltre il `.env` per-utente): eventuale
  fase successiva.
- **Permessi/ACL fini** (chi può cosa) a livello di piattaforma: oltre l'MVP.

## 3. Criteri di successo (misurabili, tech-agnostici)
- **CS-1:** per **ogni** artefatto prodotto da Sertor è dichiarato se è team-condiviso o per-utente,
  e il comportamento (versionamento/gitignore) lo rispetta in **0** eccezioni.
- **CS-2:** un secondo sviluppatore che clona il repo è operativo (RAG + wiki) ricostruendo solo il
  proprio stato per-utente, **senza** toccare né rompere il condiviso del team.
- **CS-3:** in **0** casi un segreto finisce in un file versionato.
- **CS-4:** esiste un modello esplicito e documentato di *quando/come* si condivide (almeno per
  indice e wiki), tale che due dev non producano contesto divergente in modo silenzioso.

## 4. Stakeholder e attori
- **Owner/maintainer (utente):** definisce il modello di collaborazione del team.
- **Sviluppatori del team:** consumano e contribuiscono a RAG e wiki condivisi.
- **Organizzazione enterprise:** richiede riproducibilità, sicurezza dei segreti, governance leggera.
- **Epiche a valle:** `sertor-core` (store/indice), `sertor-cli` (installer/esecuzione), il sistema-wiki.

## 5. Vincoli, assunzioni e dipendenze
- **Dipendenza dall'asse collocazione** (`igiene-radice-host`): questo tema decide *chi possiede*,
  quello decide *dove sta*; sono ortogonali ma coordinati.
- **Assunzione:** lo stack resta config-driven; le scelte di condivisione sono manopole, non hardcoded.
- **Vincolo:** segreti sempre per-utente, mai versionati (qualunque modalità).
- **Dipendenza:** capacità core già esistenti (store Azure/AI Search, adapter futuri PGVector/MongoDB).

## 6. Rischi
- **R-1 — Deriva collettiva della conoscenza:** più curatori del wiki/indice senza modello → contesto
  divergente (proprio ciò che Sertor vuole evitare).
- **R-2 — Costo dell'indice per-utente** in team grandi (ognuno embedda) → spinge verso store condiviso.
- **R-3 — Complessità del modello** (mono vs team, cosa/quando condividere) → over-engineering se non
  guidato da casi d'uso reali. *Mitigazione: affrontarla quando il caso d'uso team è concreto.*
- **R-4 — Segreti** esposti in artefatti condivisi (CS-3).

## 7. Requisiti trasversali (EARS)
- **REQ-M1 (Ubiquitous):** *The system shall make explicit, for every produced artifact, whether it
  is team-shared or per-user.*
- **REQ-M2 (Unwanted):** *If an artifact contains secrets, then it shall never be team-shared/versioned.*
- **REQ-M3 (Event-driven):** *When a second developer sets up an existing shared repo, the system
  shall let them rebuild only their per-user state without altering the shared artifacts.*

## 8. Backlog di feature (da decomporre in seguito)

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-M01 | **Modello di ownership + modalità mono/team** (driver dei default per ogni artefatto) | Rende esplicito e governabile cosa è condiviso vs privato | **Must** | bozza in [`sertor-cli/installer-multiutente`](../sertor-cli/installer-multiutente/requirements.md) (fetta-installer, da assorbire) |
| FEAT-M02 | **Collaborazione sul RAG** (indice condiviso vs per-utente; store remoto; chi/quando rebuild) | Contesto reale coerente tra dev senza ricostruire per-utente | **Should** | da decomporre |
| FEAT-M03 | **Collaborazione sul Wiki** (più curatori; merge della conoscenza; evitare deriva) | La memoria viva resta coerente a più mani | **Should** | da decomporre |
| FEAT-M04 | **Quando/come condividere** (cadenze, trigger, automatico vs manuale per indice e wiki) | Modello esplicito di pubblicazione | **Should** | da decomporre |
| FEAT-M05 | **Segreti & config per-utente** (mai versionati, ognuno il proprio ambiente) | Sicurezza + onboarding del 2° dev | **Must** | da decomporre |
| FEAT-M06 | **Governance leggera** (ruoli/responsabilità su wiki e indici) | Chi cura cosa, senza ACL pesanti | **Could** | da decomporre |

## 9. Domande aperte (le "molte sfumature" — da discutere PRIMA di decomporre)
- **[DA-M-a]** Matrice condiviso↔privato definitiva per OGNI artefatto (config, indice, wiki, env,
  `.venv`, lockfile, `.mcp.json`): la bozza installer copre alcuni; va completata col team in testa.
- **[DA-M-b]** L'**indice RAG** è condiviso (store remoto, costruito una volta) o per-utente (Chroma
  locale)? Se condiviso: chi lo ricostruisce e quando? Come si evita contesto stantio tra dev?
- **[DA-M-c]** Il **wiki** scritto a più mani: modello di cura/merge della conoscenza; un curatore
  designato o cura distribuita? Come si applica il rituale di step in team?
- **[DA-M-d]** **Quando** si condivide: a ogni commit? Su trigger? Con quale cadenza? Cosa è
  automatico (hook/CI) vs manuale?
- **[DA-M-e]** La **modalità** (mono/team) è per-install o **per-progetto** (registrata nella config
  condivisa, così ogni dev eredita lo stesso modo)?
- **[DA-M-f]** **Riproducibilità vs pulizia**: lockfile condiviso (deterministico) o ambiente
  per-utente? (la bozza installer ha scelto per-utente per il mono).
- **[DA-M-g]** **Governance**: serve un modello di ruoli/permessi, o basta la convenzione + git?

> **Nota di processo.** Epica APERTA come contenitore; **non decomporre ora**. Si riprende quando il
> caso d'uso team diventa concreto, partendo dalle domande aperte sopra (R-3: evitare over-engineering
> senza un caso reale).
