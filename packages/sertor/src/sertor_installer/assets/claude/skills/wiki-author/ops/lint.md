# Operazione `lint` — verifica di coerenza

> **Modulo operazione.** Esecutore: **A** = curator OK · **B/C** = solo flusso principale (Opus).
> Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, voce di log §6) vedi il playbook
> `wiki-playbook.md`; il lint **C** giudica contro **come dev'essere una pagina**
> ([`../page-craft.md`](../page-craft.md)) e **come dev'essere l'insieme** ([`../wiki-craft.md`](../wiki-craft.md)).
> Qui solo la procedura specifica.

Il lint ha **tre livelli**: **A** strutturale (meccanico, CLI: igiene), **B** semantico (giudizio, LLM:
*claim ↔ realtà del repo*) e **C** organizzativo (giudizio, LLM: *collocazione/atomicità/link*). A è la
baseline; B e C sono ortogonali (puoi lanciarli insieme o separati). **Non auto-correggere** di default:
produci un **report con severità** e correggi **solo su conferma** (o se il brief lo richiede); l'applicazione
del refactoring organizzativo è l'operazione `reorg` (`ops/reorg.md`). Voce di log `lint` (opzionale ma
consigliata se correggi).

**Ambito: cosa lintare (`[[audit]]`).** Il lint **non** è solo sul wiki: copre i target dichiarati in
`[[audit]]` (config). Ogni target = `paths` (glob dell'ospite) + `kind` (profilo universale qui sotto).
**Prima regola che matcha vince** (i `paths` più specifici vanno prima): così `TODO.md`/`tasks.md`/
`checklists` ricadono in `tracker` anche se stanno sotto `requirements/`/`specs/`. Il `kind` determina
**quali livelli** si applicano e **cosa conta come deriva** — è ciò che evita i falsi positivi (non trattare
l'*intento* come *stato*; gerarchia di autorità: codice/test = comportamento, requisiti/spec = perché).

| `kind` | Liv. A (strutturale) | Liv. B (semantico) — cos'è "deriva" | Azione default |
|---|---|---|---|
| `wiki` | **sì** (CLI: wikilink/frontmatter/orfani/naming) | claim descrittivo contraddetto da codice/test · contraddizioni tra pagine · coverage · sommario stantio | report |
| `requirements` | no (niente wikilink/frontmatter) | **solo claim di STATO** (implementato/mergiato/conteggi/ID); un «*shall X*» non ancora in codice = **backlog, NON deriva** | report |
| `spec` | no | come `requirements` + coerenza col codice **se** lo stato dichiara "implementato" | report |
| `tracker` | no | **tabelle/checkbox di stato** ("FATTO/da fare", `[x]`/`[ ]`) contraddette dalla realtà = **deriva diretta** | report |

**A) Lint strutturale — 100% meccanico (CLI).** Esegui `sertor-wiki-tools lint --json` **e**
`… validate --json`; interpreta i contratti `wiki.lint/1` (wikilink rotti, orfani, frontmatter mancante,
naming). **Non** rifare Glob/Grep a mano. È autorevole sui link: se la CLI dice 0 broken, i link sono a posto.
Nota sui **forward-link**: un `[[…]]` verso un nodo da creare **non** va lasciato a vuoto (sarebbe `broken`,
indistinguibile da un refuso) → si crea una pagina-**stub** (`status: stub`, vedi `../page-craft.md`), così il
link risolve. Quindi: target con file (anche stub) = ok; target senza file = `broken` (refuso da correggere).
Il `lint` espone gli stub nel campo **`stubs`** del contratto (worklist dei *nodi da riempire*), distinto dai
difetti: uno stub non è un errore, è un nodo voluto in attesa di contenuto.

**B) Lint semantico — giudizio (LLM, flusso principale).** Verifica che gli **artefatti dichiarati in
`[[audit]]`** (non solo il wiki: anche `requirements`/`spec`/`tracker`) **non siano derivati** dalla realtà
del progetto, applicando il **profilo del `kind`** (tabella sopra). È **giudizio**: resta all'LLM e **di
norma al flusso principale (Opus)**, che ha il
contesto; **non si delega al `curator` (Haiku)** la parte di giudizio (vedi indice §7 e il rituale in `CLAUDE.md`).
Procedura ripetibile:

1. **Baseline** = il report di (A).
2. **Estrai i claim verificabili** dalle pagine (usa `collect` per l'inventario): conteggi (test, moduli,
   lingue…), stati (`mergiata`, `in progress`, branch/PR/commit), versioni, date, percorsi/simboli citati come
   esistenti, nomi di entità. *(Per fan-out su molte pagine puoi delegare l'ESTRAZIONE a reader; il giudizio resta tuo.)*
3. **Recupera la ground truth dal repo** — appòggiati agli strumenti **già disponibili**, non reinventarli:
   - **git** (stato/PR/branch/commit) → **delega al ruolo VCS** (`[roles].vcs`); le operazioni git non si eseguono qui.
   - **esistenza file/simboli, valori nel codice** → il **RAG dell'ospite** se configurato (server MCP del corpus
     codice: `search_code`/`find_symbol`/`search_docs`); **altrimenti** ispezione diretta (`Read`/`Grep`).
   - **conteggi build/test** → il tool dell'ospite (es. `pytest --collect-only -q`).
4. **Confronta claim ↔ ground truth → giudica.** Un claim è una **deriva** se il repo lo contraddice. Tassonomia
   dei controlli: *stato git/PR/branch superato* · *numeri incoerenti col codice* · *file/simboli citati ma assenti*
   · *date/versioni vecchie* · *contraddizioni tra pagine* · *claim più vecchi delle `sources`* · *coverage* (cose
   reali del progetto non ancora documentate).
5. **Report con severità** (Alto/Medio/Basso/Info) + proposta di correzione per ciascun finding. **Scarta i falsi
   positivi** (es. un reader che segnala link "inesistenti" già smentiti dalla CLI).
6. **Correggi su conferma.** Aggiorna **solo le pagine attive** (stato corrente); **non riscrivere** il registro
   storico del log né gli artefatti datati. Appendi una voce di log `lint`.
7. **Quando il finding è una pagina-superata** (non un refuso da correggere: la pagina nel suo insieme è
   contraddetta dall'autorità — codice/test sul comportamento, decisione registrata sul perché), applica la
   **supersession esplicita** del playbook §4 (*Verità, autorità e obsolescenza*): `status: superseded` +
   banner datato con link alla verità corrente. **Mai cancellare d'ufficio**: la pagina si pota/fonde solo
   in un `reorg` confermato. La gerarchia con cui giudichi il conflitto è quella della stessa sezione del playbook §4.

**Host-agnostico (degradazione per profilo).** I probe disponibili dipendono dall'ospite: su un host **solo-doc**
non ci sono test/simboli di codice → salta i probe di codice e tieni i controlli su date/contraddizioni/coverage;
su **solo-code** salta i controlli doc-specifici. git è quasi sempre disponibile; il RAG è un **acceleratore se
c'è**, mai un prerequisito (fallback su `Read`/`Grep`). Non assumere `pytest`/`src/`: derivali da `source_dirs`/profilo.

**Al commit (comportamento-obiettivo: A + B incrementale).** Al commit gira il livello **A** (strutturale, sui
target `wiki`) **e** il livello **B** **solo sugli artefatti del changeset** (incrementale, mai l'intero repo),
per ogni `kind`; esito = **report + warning NON bloccante** (mai blocco, mai auto-fix — lezione: il valore sta
nella rilevazione, non nella correzione automatica). **Caveat di automazione:** A al commit è meccanico
(hook/CLI); **B al commit è un giudizio LLM** → la sua esecuzione automatica dipende dall'orchestrazione/trigger
(lato deterministico, cfr. `ops/generate.md` e il contratto-trigger, oggi non cablato). Finché non è cablata:
il warning al commit copre A e **ricorda di lanciare B incrementale** (`/wiki lint` sul changeset).

**C) Lint organizzativo — giudizio (LLM, flusso principale).** Verifica che il wiki sia un **grafo ben
organizzato** (criteri in [`../wiki-craft.md`](../wiki-craft.md): archetipi, pagine di struttura, due assi,
SSoT, no frammentazione), non solo igienicamente sano. È **tutto giudizio**: collocazione e natura di una pagina **non
sono deterministiche** — cartella e `type` possono concordare tra loro e **mentire entrambi** sul contenuto,
quindi nessun controllo meccanico le coglie. Resta al flusso principale (Opus), **non** al `curator`. Si
applica al solo `kind` `wiki`, **on-demand** (non al commit). Inventario di partenza: `collect`
(rel_path/area/`type`/tags/wikilink); i **backlink non sono esposti** dalla CLI → **calcolali invertendo** i
`wikilinks` di `collect`. Controlli:

1. **Collocazione vs natura** — la natura reale della pagina non corrisponde all'area che la ospita (es. un
   record di feature in `syntheses/`). Riferimento: l'euristica di collocazione nel playbook §3.
2. **`type` semanticamente falso** — `type` coerente con la cartella ma non col contenuto (deriva
   natura↔collocazione).
3. **Tassonomia collassata** — un'area usata come discarica (quota sproporzionata di pagine, specie in
   un'area "rara" come `syntheses/`) mentre altre aree dichiarate restano vuote pur esistendo contenuto che
   le riempirebbe.
4. **Atomicità** — pagine con più focus o sezioni duplicate (candidate a split; vedi `page-craft.md` §1).
5. **Disciplina dei link** — link relegati a "vedi anche" invece che inline; pagine centrali ma debolmente
   connesse (pochi backlink). Vedi `page-craft.md` §3.

Esito = **report con severità + proposta** per finding (sposta a `<area>` · correggi `type` · splitta ·
aggiungi link inline), **nessun auto-fix**. L'applicazione su conferma è l'operazione `reorg` (`ops/reorg.md`).
