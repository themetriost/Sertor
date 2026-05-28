---
description: Deriva (data-driven) gli entity_types ottimali per GraphRAG dal corpus già indicizzato (code+doc), come proposta da approvare
argument-hint: "[opz.: collection / n. cluster / path indice — default: baseline_azure_large, 14]"
---

Determina gli **`entity_types` migliori per l'estrazione GraphRAG** analizzando ciò che è
**già indicizzato** nei due lati del corpus (codice + documentazione), invece di sceglierli a
mano o affidarli al `prompt-tune` generico. Ambito/override richiesti: $ARGUMENTS.

Principio guida (vedi `CLAUDE.md`): tool **riusabile e repo-agnostico**, output come
**proposta da far approvare** all'utente — niente auto-apply su `settings.yaml`.

## Idea
- Il lato **codice** non va "indovinato": i suoi *kind* (module/class/function/method) e i
  simboli centrali si leggono dal **grafo AST** (deterministico, gratis).
- Il lato **doc** è dove serve l'induzione: si clusterizzano gli **embedding già presenti** in
  Chroma (coverage-aware) e si etichettano i temi ricorrenti → tipi `concept`/`feature`.
- Il valore finale sono i **tipi-ponte** che legano concetto ↔ simbolo ↔ doc.

## Procedura
1. **Evidence pack (deterministico, no LLM).** Esegui lo script dal venv principale:
   ```bash
   PYTHONPATH=. .venv/Scripts/python.exe shared/derive_entity_types.py [--collection <nome>] [--clusters <K>] [--index-path <path>] [--graph <graphml>]
   ```
   Scrive `03-graphrag/entity_types_evidence.md` (+ `.json`). Per un altro repo/indice basta
   cambiare `--index-path`/`--collection`/`--graph` (parametri, niente codice da toccare).
2. **Leggi** `03-graphrag/entity_types_evidence.md`: kind+simboli centrali del codice, e i
   cluster doc con i loro chunk rappresentativi.
3. **Induci la tassonomia**:
   - *Tipi di codice (coarse)* dai kind/simboli AST: tieni i salienti e navigabili
     (es. `class`, `function`, `module`, `exception`, `endpoint`); **unisci method→function**;
     **non** scendere a granularità fine (parameter/variable/decorator) che l'AST già copre e
     che fa solo rumore.
   - *Tipi concettuali* dai cluster doc: nomina i temi ricorrenti (es. concetti/feature di
     dominio). **Scarta i cluster-rumore** (release notes, changelog, traduzioni, boilerplate).
   - Per un'app di business, qui emergono le **entità di dominio** (es. Order, Customer): tienile.
4. **Proponi** all'utente, in modo conciso:
   - lista finale `entity_types` (~6-9, mix codice-coarse + concetti/dominio), con 1 riga di
     razionale per tipo;
   - 2-3 **esempi few-shot reali** (entità viste nell'evidence con il tipo assegnato), utili a
     tarare il prompt di estrazione;
   - cosa hai **escluso** (cluster-rumore) e perché.
   Chiedi conferma o aggiustamenti. **Non** modificare `settings.yaml` senza ok.
5. **Su approvazione**: aggiorna `03-graphrag/grag/settings.yaml` → `extract_graph.entity_types`
   (e, se serve, gli esempi in `prompts/extract_graph.txt`). Ricorda che cambiare i tipi cambia
   il prompt → **cache miss** → il prossimo `graphrag index` ri-estrae da capo (costo pieno).

Confronto: questa derivazione data-driven è da preferire al `graphrag prompt-tune` generico
perché sfrutta lo split codice/doc e riusa il grafo AST; il prompt-tune resta un baseline utile.
