---
name: "skill-review"
description: "Revisiona una skill ESISTENTE (un SKILL.md + il suo payload: template, references, contract) e produce un feedback ordinato per priorità — bloccanti prima, migliorie poi — senza riscriverla. Usa questa skill ogni volta che l'utente vuole: rivedere/valutare/auditare/dare feedback su una skill già scritta (propria o di un altro workspace/team); capire se una skill è eseguibile 'a freddo' da un agente che riceve solo il suo corpo; verificare se le regole di una skill reggono a input ostili o a sessioni lunghe; controllare host-agnosticità e parità prima di distribuirla; sapere cosa manca a una skill rispetto alle skill mature. Applica la lente 'garanzie per-costruzione vs per-promessa', il test del freddo e una checklist di dimensioni. NON usarla per CREARE, riscrivere o ottimizzare una skill: quello è `skill-authoring`, a valle. NON usarla per rivedere un AGENTE (subagent con tools/model e prompt): quello è `agent-review`. skill-review CRITICA e propone; non produce né edita il SKILL.md."
argument-hint: "Il percorso (o il contenuto) della skill da rivedere: SKILL.md + payload (templates/, references/, contract); più eventuali domande specifiche dell'autore"
compatibility: "Nessuna dipendenza di runtime: la review è giudizio ancorato al corpo della skill e al suo payload"
metadata:
  author: "sinthari"
  capability: "skill-review"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

`$ARGUMENTS` indica la skill da rivedere: tipicamente il percorso di una cartella-skill (`SKILL.md` +
`templates/` / `references/` / contract), oppure il contenuto incollato, più eventuali domande a cui
l'autore vuole risposta.

## Cosa sei, in questo flusso

Sei **il revisore** di una skill già scritta. Il tuo prodotto è un **feedback ordinato per valore**,
non una riscrittura: individui il rischio, lo spieghi, proponi la correzione concreta (anche uno
snippet), ma **non editi** il SKILL.md — quello, se serve, lo fa `skill-authoring` a valle. Rivedi il
corpo e il payload per come li riceverebbe un altro agente, non per come li immagina l'autore.

Leggi **tutto** il payload prima di giudicare: `SKILL.md`, i template, i `references/`, i contract.
Se un giudizio dipende da qualcosa che non è nel materiale, **dillo** invece di indovinare.

## La lente centrale: per-costruzione vs per-promessa

È la mossa che dà valore a una review. Per ogni regola/garanzia della skill, chiediti da cosa è
difesa:

- **Per-costruzione** — la fa un runtime deterministico, uno schema, un gate meccanico. Regge da
  sola: l'agente non può violarla anche volendo.
- **Per-promessa** — la tiene il **giudizio dell'agente** (una regola nel prompt, una convenzione).
  Può cedere sotto pressione, deriva, o distrazione.

**Il rischio residuo di una skill vive quasi sempre nelle regole per-promessa.** Su ciascuna,
la tua domanda non è «è scritta bene?» ma:

1. **Regge sotto pressione?** Input ostili/fuorvianti dell'utente («dammi la risposta», «ignora i
   criteri»), sessioni lunghe (deriva della memoria dello stato).
2. **Si può spostare a costruzione?** È la correzione più forte: trasforma una promessa in una
   garanzia. *(Esempio reale: «i criteri restano nascosti» difeso da un commento HTML nel file è una
   promessa fragile; un comando di runtime che emette solo la parte visibile lo rende vero per
   costruzione.)*
3. **Se non si può, è armata e dichiarata?** Aggiungi il **perché** (un agente capace tiene la linea
   meglio quando sa il motivo) e **dichiara il confine** della garanzia (vedi threat-model sotto).

## Il test del freddo (eseguibilità a freddo)

Simula un agente che riceve **solo** il corpo della skill + il payload bundlato, senza il repo di
sviluppo intorno. Dove inciampa? I buchi ricorrenti:

- **Schemi di input non specificati** — la skill dice «passa un file JSON» ma non ne dà la forma.
  L'agente si ferma o indovina. → gli schemi (input e output `--json`) vanno **bundlati** in
  `references/`, non lasciati nel repo di sviluppo (progressive disclosure).
- **Payload referenziato ma non bundlato / puntamento live-repo** — un rimando a
  `specs/…/contracts/` che in una copia distribuita non si risolve. → far **viaggiare** i contratti
  con la skill.
- **Una regola dura che contraddice un'istruzione operativa** — es. «nessuna mutazione fuori dal
  CLI» accanto a «salva il file in `.../evidenza/`». Un agente *fail-loud* può **congelarsi** (la
  regola del fermarsi lo autorizza). → riconciliare il wording, distinguendo i due casi.

## Checklist delle dimensioni

Passa la skill su queste dimensioni; per ognuna, findings concreti (non «si potrebbe migliorare»):

1. **Eseguibilità a freddo** — schemi di input/output presenti e bundlati? payload risolvibile?
   contraddizioni regola↔istruzione che bloccano?
2. **Robustezza sotto pressione/deriva** — c'è una contromossa esplicita agli input ostili sulle
   regole per-promessa? lo stato si ri-allinea da una fonte di verità o si «ricorda» (rischio
   deriva)?
3. **Divisione giudizio↔determinismo (D↔N)** — qualcosa fatto a giudizio che andrebbe spinto nel
   runtime (o viceversa)? occultamenti/validazioni affidati a disciplina invece che a costruzione?
4. **Confini dichiarati (threat-model)** — ogni garanzia deterministica ha un confine: è dichiarato?
   *(Es.: un comando che nasconde contenuto difende il canale agente↔utente, non i dati a riposo —
   va detto.)*
5. **Host-agnosticità e parità** — corpo senza path assistant-specifici, payload citato **per
   nome**, nessuna slash-command nel corpo, comandi come vehicle pubblico del progetto. Se
   distribuita: **doppia-casa byte-identica** (la sorgente della skill e la sua copia installata nell'assistente)
   con un parity-guard (anche solo un check `diff`/`sha256`).
6. **Progressive disclosure** — SKILL.md snello (< ~500 righe); schemi/contratti lunghi in
   `references/` con puntamento chiaro; tabella dei contenuti per i reference grandi.
7. **Il perché sulle regole di giudizio** — le regole per-promessa portano la ratio, non solo il
   MUST.
8. **Maturità** — c'è un **esempio lavorato** end-to-end? una sezione **troubleshooting** dei modi
   di guasto reali? esempi input→output dove servono? La `description` triggera bene (frasi naturali,
   un po' «pushy», e distingue da skill adiacenti)?

## Come scrivere il feedback

- **Ordina per valore**, non per sezione. Prima i **bloccanti** (rendono la skill fragile o non
  eseguibile a freddo), poi le **migliorie**, poi le rifiniture. Numera i findings (es. B1, M1) così
  l'autore può rispondere punto per punto.
- **Ogni finding porta la correzione**, concreta: la regola riformulata, lo snippet, il comando.
  Un finding senza rimedio è una lamentela.
- **Rispondi alle domande specifiche dell'autore** una per una, se le ha poste.
- **Residui onesti, non gonfiati.** Trova il *prossimo strato* di rischio — non timbrare — ma
  dichiara i residui come **confini** (threat-model), non come bug inventati. Non fabbricare findings
  per sembrare esaustivo.
- **Reciprocità.** Se dalla skill che rivedi impari un pattern migliore del tuo, **dillo**: la review
  è a doppio senso e la restituzione onesta vale più di un timbro.
- **Apri col merito.** Nomina ciò che è già forte (e va difeso così com'è) prima di elencare i buchi:
  ancora il giudizio e rispetta il lavoro fatto.

## Se la skill è di un altro workspace/team

Consegna il feedback **depositando un file** nel canale di scambio del progetto che l'ha chiesta (di
norma la loro cartella di intake `wiki/sources/input-other-agents/`), con provenienza esplicita
(chi, quando, in risposta a cosa). **Non eseguire MAI operazioni git nel loro repo** (commit, push,
branch, PR): nei repo altrui si depositano solo file — è una regola aurea. Se serve una seconda
passata dopo che hanno incorporato, ripeti il ciclo depositando un nuovo file.

## Confine con `skill-authoring` e `agent-review`

skill-review **critica e propone**; non crea, non riscrive, non ottimizza. Quando il passo è
*produrre o modificare* un SKILL.md — scrivere la skill nuova, applicare le correzioni, ottimizzare
la description, girare gli eval — quello è `skill-authoring`. Le due si passano il testimone: review →
(decisione dell'autore) → authoring.

Se ciò che ti chiedono di rivedere è la definizione di un **agente** (un'intestazione con `tools` e
`model` più un prompt, avviato da un brief), la review è `agent-review`: applica queste stesse lenti al
prompt e aggiunge ciò che solo un agente ha (intestazione, contratti del brief e del rapporto, confine
d'autorità, parità fra assistenti).
