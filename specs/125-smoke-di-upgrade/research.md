# Research — smoke di upgrade

**Feature**: `125-smoke-di-upgrade` (E15-FEAT-012) · **Date**: 2026-07-29

---

## R1 — Estendere lo script esistente, non scriverne un secondo

**Decision**: aggiungere un parametro **`-FromRef`** a `scripts/smoke.{ps1,sh}`. Valorizzato → lo
script installa **da quel ref**, poi aggiorna a `-Ref`, poi asserisce gli esiti. Assente → comportamento
odierno, invariato.

**Rationale**: il docstring del wrapper `pytest` dichiara già il perché di quella forma — *«lo script
che un dev lancia a mano è quello che gira in CI, così non possono divergere»*. Vale identico per
l'aggiornamento: un secondo harness introdurrebbe **proprio la divergenza** che il primo è stato scritto
per evitare, e la introdurrebbe sul percorso che è già il meno osservato.

Lo script ha inoltre già ciò che serve: `Fail`, `Require-Tool`, `Assert-Path`, `Assert-MarkerInFile`,
la costruzione delle sorgenti `git+$RepoUrl@$Ref#subdirectory=…`, l'ambiente ripulito dalle `SERTOR_*`
ereditate e un host sintetico neutro creato in temp.

**Alternatives considered**:
- **Un secondo script `upgrade-smoke.*`** — duplicherebbe la creazione dell'host, la pulizia
  dell'ambiente e le asserzioni comuni. Due copie che divergono è il difetto che stiamo misurando,
  applicato allo strumento che lo misura.
- **Farlo in Python nel test** — scartato per la stessa ragione per cui non è stato fatto la prima
  volta: la logica in Python **non** è ciò che un dev esegue a mano, quindi diverge in silenzio.

---

## R2 — Come si determina «la release precedente»

**Decision**: **derivata** dal riferimento pubblico — l'ultimo tag pubblicato — non scritta a mano.

**Rationale**: è il **Principio XIV applicato al meccanismo stesso**. Un elenco di versioni in un file
di CI sarebbe una copia di un fatto che vive altrove, e invecchierebbe **esattamente** come tutte le
copie che questo progetto ha già pagato. Se il tag esiste, il fatto è derivabile; derivarlo costa un
comando.

**Nota di scope (Q1 risolta):** ogni combinazione parte dall'**ultima** release; **una sola** esercita
anche un **salto lungo**. La matrice esaustiva «ogni versione → l'ultima» è una **misura una-tantum**,
non un gate ricorrente → vive come **E15-FEAT-014**.

---

## R3 — Quali esiti asserire, e perché proprio questi

**Decision**: gli esiti derivano dai **difetti realmente occorsi**, uno per uno, non da un elenco di
ciò che si potrebbe verificare.

| Esito asserito | Difetto reale che lo giustifica |
|---|---|
| il **pin punta alla versione in uscita** | pin fermo dopo l'upgrade — segnalato da **tre nodi indipendenti** |
| l'automatismo di sessione è **uno solo** e aggiornato | hook **duplicati** al ri-cablaggio (E10-FEAT-032) |
| la **configurazione dell'ospite è preservata** | il fix di E2-FEAT-022 rischiò di azzerare il corpus a ogni upgrade — colto da una prova manuale, **non dai test** |
| la **forma dell'invocazione** registrata è quella corrente | `--directory` conservato perché «c'era già», RAG cieco per un mese |
| la **salute** dell'host è verde dopo l'aggiornamento | verifica d'insieme: coglie ciò che le quattro sopra non nominano |

**Rationale**: è il criterio SC-001 reso operativo. Un elenco costruito per completezza teorica
proteggerebbe da difetti immaginati; questo protegge da difetti **avvenuti**, ed è verificabile
all'indietro.

**Dove vive l'elenco (FR-015)**: in **un solo punto** dello script, come sequenza nominata di
asserzioni. Aggiungerne una dopo un difetto nuovo deve essere una riga in più, non una
ristrutturazione — altrimenti l'elenco invecchia e la verifica protegge solo il passato.

---

## R4 — Distinguere l'impedimento d'ambiente dal difetto di prodotto

**Decision**: due esiti di fallimento distinti. Un prerequisito assente (rete, `uvx`, tag non
raggiungibile) **non** è un rosso di prodotto: viene dichiarato come impedimento, con la causa.

**Rationale**: è FR-011, ed è la condizione di sopravvivenza del gate. Un rosso indistinto insegna a
ignorarlo — la stessa dinamica per cui la v0.3.3 è esistita (*una guardia che segnala il falso insegna
a smettere di leggerla*). Lo script ha già `Require-Tool` per i prerequisiti: la distinzione va **estesa**
a ciò che l'aggiornamento richiede in più, non inventata da capo.

---

## R5 — Due percorsi d'esecuzione (Q2 risolta)

**Decision**:
- **Automatico**, vincolante al rilascio: **una** combinazione, dall'ultima release.
- **Completo**, avviabile **a richiesta**: tutte le combinazioni, più il **salto lungo**.

**Rationale**: la risposta dell'utente ha separato **quando** si esegue da **quanto** si copre — un
asse che le tre opzioni proposte non offrivano, perché davano per scontato che copertura e costo
fossero la stessa manopola. Così il controllo che deve girare *sempre* resta economico e la copertura
piena resta **disponibile** invece che sacrificata.

**Conseguenza da rispettare (FR-013):** l'esclusione della verifica completa dal percorso automatico va
**dichiarata dove la si documenta**. Una copertura che esiste ma nessuno sa di dover lanciare è
copertura solo sulla carta.

---

## R6 — Cosa NON fa questa feature

- **Non corregge** i difetti che rileverà: `upgrade` non viene toccato. Se la prima esecuzione mostra
  che uno dei tre fix di oggi non arriva a un ospite che aggiorna, quello è un **finding**, e si chiude
  altrove.
- **Non sostituisce** lo smoke d'installazione: sono due domande diverse — *un ospite nuovo ottiene la
  capacità?* e *un ospite esistente la riceve aggiornando?*
- **Non copre le configurazioni che non abbiamo**: cinque difetti su sette è il bersaglio, e i due
  restanti vanno **dichiarati** (SC-007), non taciuti.

---

## Out of scope (promossi, non sepolti)

- **Matrice esaustiva «ogni versione → l'ultima»**: **E15-FEAT-014**, misura una-tantum.
- **Il debito del gate documentato** (`testpaths = ["tests"]` → il comando dichiarato «gate vincolante
  pre-merge» raccoglie 1385 test su ~2517): correlato ma distinto, e va corretto **a parte** — è un
  errore di un documento sempre attivo, non di questa verifica.
