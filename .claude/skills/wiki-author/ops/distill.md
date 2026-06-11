# Operazione `distill` — estrai le entità durevoli, assottiglia i record

> **Modulo operazione.** Esecutore: **solo flusso principale (Opus)** — è giudizio (cosa è un'entità, come
> astrarla), non trascrizione: non si delega al `curator` (Haiku), come il lint B/C e `reorg`. Per il
> **substrato condiviso** (tassonomia §3, voce di log §6) vedi `wiki-playbook.md`; per **se/cosa merita una
> pagina** [`../wiki-craft.md`](../wiki-craft.md) (§1 + la *lente di prodotto* §2), per **come si scrive la
> pagina-entità** [`../page-craft.md`](../page-craft.md). Qui solo la procedura specifica.

La distillazione è il **duale** di `record`: se `record` cattura l'**evento datato**, `distill` ne estrae la
**conoscenza durevole** in pagine-entità proprie, così non resta sepolta nel diario di sessione. Tre
**ingressi**, stesso giudizio:

- **di step** (il caso tipico): secondo tempo del rituale (subito dopo `record`, vedi il rituale dell'ospite,
  es. nel `CLAUDE.md`) — una **feature appena implementata**: il record nasce *magro per costruzione*
  (evento + esito + puntatori), le entità in pagine;
- **da backlog**, su richiesta: un vecchio record già grasso da assottigliare;
- **da conversazione**: il **brief condensato** di una conversazione/sessione
  **intera** — anche vecchia, mai registrata in tempo reale, o avvenuta altrove — da riversare nel grafo.
  **Mai il transcript grezzo**: chi invoca condensa prima (l'input arriva già pre-elaborato).
  È il *paracadute* per quando il rituale non c'era. Se il brief contiene anche **eventi** non a diario
  (lavoro svolto mai registrato), un `record` contestuale li cattura: `distill` scrive il durevole nel
  grafo, non fa cronaca.

1. **Materiale di partenza.** Il lavoro appena svolto (codice toccato + il record `experiment` appena
   scritto), oppure — in modalità backlog — una pagina grassa esistente da distillare, oppure — in modalità
   conversazione — il brief condensato di una sessione (decisioni, concetti, esiti). `collect --json` per
   sapere quali entità hanno già una pagina (anti-duplicato).
2. **Enumera i candidati-entità.** Dal materiale, elenca i costrutti con **identità propria**: entità di
   dominio, porte/contratti, adapter, servizi, decisioni architetturali, tecnologie (la *lente di prodotto*
   in [`../wiki-craft.md`](../wiki-craft.md) §2).
3. **Filtra (test di [`../wiki-craft.md`](../wiki-craft.md) §1).** Tieni solo i candidati con **nome stabile**
   e **referenziati da più punti**; scarta il dettaglio implementativo (un metodo privato non è una pagina).
   **Anti-frammentazione:** poche pagine vive, non una micro-pagina per ogni classe.
4. **Crea/arricchisci la pagina** di ogni candidato superstite, nell'area giusta (tassonomia §3), secondo
   [`../page-craft.md`](../page-craft.md): **definizione in apertura** («X è…»), il *perché*, le **relazioni
   coi vicini** (entità→porta→adapter→servizio), claim **evergreen** ancorato. Se la pagina esiste ed è già
   ricca, **non duplicare** (idempotenza).
5. **Assottiglia la sorgente.** Rimuovi dal record/pagina-grassa la conoscenza-entità migrata e sostituiscila
   con **puntatori** `[[entità]]`. Il record `experiment` resta **evento + esito + link**, non un trattato —
   è lo stesso confine di [`../log-craft.md`](../log-craft.md) §1 (log↔pagina), applicato a record↔entità. Non
   duplicare gli **artefatti di processo** che vivono altrove (spec/plan/tasks/Constitution Check, tabelle di
   rischi/decisioni, hash git): **citali**, non ricopiarli — l'esito sta in una riga. E non trascrivere il
   **codice** in snippet (è la prima fonte di deriva): descrivi e cita il file (vedi [`../page-craft.md`](../page-craft.md)).
6. **Backlink + indice + voce di log.** Linka le nuove pagine dall'indice e dalle correlate; appendi UNA voce
   di log `distill` (formato: playbook §6; come si scrive: [`../log-craft.md`](../log-craft.md)).
