# Research & decisions — Daily distill floor (E10-FEAT-039)

Le due forcelle di **prodotto** erano già decise dall'utente (2026-07-22): **pavimento persistente** +
**segnale audit = wikilink + prosa**. Qui si sciolgono le 5 domande aperte di dettaglio (DA-1..5 dei
requisiti), tutte a livello di plan.

## DA-1 — Scope del corpus e regola «entità candidata in prosa»

**Decisione.**
- **Reference-counting scope** = tutti i `.md` sotto la root del wiki **incluse le partizioni di log**
  (è lì che la conoscenza si accumula «sepolta nel record datato», il caso Acta), **escluso** l'`index.md`.
  `requirements/` **fuori scope MVP** (config flag futura `[ritual].audit_extra_dirs`, Could) — bounding.
- **«Ha una pagina»** = esiste una **content page** (via `iter_pages`, che esclude index+log) il cui alias
  (`rel_path` | `no_ext` | `stem`, come `ritual_check._link_aliases`) combacia col nome candidato
  (case-insensitive).
- **Segnale (i) wikilink penzolanti** (alta precisione): `[[x]]` il cui target non è in `target_index` →
  candidato; frequenza = n. di **punti distinti** (pagine sorgente) che lo citano.
- **Segnale (ii) prosa** (regola fissa, deterministica, NO NLP): **span in backtick** `` `token` `` il cui
  `token` è un **identificatore** (`^[A-Za-z][\w.\-/]{2,}$`), non stopword, senza pagina. Motivo: in un wiki
  tecnico le entità durevoli citate in prosa sono quasi sempre backtickate (comandi, simboli, chiavi di
  config: `subscribe`, `search_combined`, …) → alta precisione senza NLP. La capitalizzazione libera in
  prosa è **rumorosa** (R-1) ed erode il confine D↔N → **esclusa** dall'MVP (leva futura). *Questo soddisfa
  «wikilink + prosa» restando deterministico.*
- Un candidato può avere segnale `wikilink`, `prose` o `both`; si fondono per nome normalizzato.

## DA-2 — Nuovo verbo `distill-audit` vs flag su `ritual-check`

**Decisione: nuovo verbo `distill-audit`.** Lo *scope* è diverso — `ritual-check` opera sul **git-diff dello
step** (cosa è cambiato ora), `distill-audit` sull'**intero corpus cross-sessione** (cosa si è accumulato).
Sono complementari (gemelle FEAT-026), non lo stesso comando con un flag: mescolarli confonderebbe la
superficie CLI e i contratti. Nuovo modulo `distill_audit.py`, nuovo contratto `wiki.distill_audit/1`.

## DA-3 — Come l'hook rileva «giornata attiva» e «voce distill del giorno»

**Decisione.**
- **«Voce distill del giorno» = pavimento soddisfatto** se la partizione di log del giorno
  (`<log_dir>/<YYYY-MM-DD>.md`) contiene una voce con operazione `distill` (heading nel `log_format`
  `## [YYYY-MM-DD] distill | …`). Rilevazione deterministica via regex sul file del giorno.
- **Il «no» soddisfa il pavimento** perché va anch'esso **registrato come voce di log `distill`** (titolo
  tipo «no: <ragioni>» che nomina i candidati) — così l'hook vede la stessa voce, e il «no» **costa** una
  scrittura di log che nomina i candidati (chiude DA-3 e REQ-012 insieme, elegante).
- **«Giornata attiva»**: l'MVP sollecita quando **N>0 e nessuna voce distill del giorno**; il debito N>0 è
  di per sé il proxy di «c'è lavoro di distillazione in sospeso». Il gating aggiuntivo su «attività della
  sessione» (via `scan pending`) è **Could** (evita rumore su giornate idle con N>0; non-MVP).

## DA-4 — Estendere `wiki-pending-check` vs nuovo hook

**Decisione: nuovo hook `distill-floor.py`.** Concern distinto (pavimento distill) da `wiki-pending-check`
(record pending) e con un **evento in più** (`SessionStart`, che `wiki-pending-check` non ha). Shoehorn-arlo
nei due hook esistenti (uno Stop/SessionEnd, uno SessionStart) frammenterebbe la logica su due file. Un
asset coeso wirato ai **3 eventi** è più chiaro e testabile — stesso pattern di `rag-freshness.py` +
`rag-freshness-start.py`, ma qui **un solo file** parametrico su `--mode`.

## DA-5 — Once-per-day: dove persiste lo stato

**Decisione: `.sertor/.distill-floor.json`** (come `.sertor/.rag-health.json`), best-effort, secret-free:
`{"date": "YYYY-MM-DD", "debt": N, "top": ["a","b","c"], "audited_at": "…Z"}`. Su `SessionStart` l'hook
esegue l'audit e scrive la cache; su `Stop`/`SessionEnd` riusa la cache se è del giorno (evita il riscan a
ogni turno, NFR-5), altrimenti la ricalcola. La cache è un artefatto rigenerabile in `.sertor/` (già
git-ignored come gli altri).

## Note trasversali

- **Confine D↔N onorato ovunque:** il tool non giudica la durevolezza; l'hook non giudica né blocca;
  l'atto di distillare (o il «no» motivato) resta nell'agente.
- **Limite onesto del pavimento:** un hook vede solo *se esiste una voce distill del giorno*, non se è
  genuina → un «no» falso resta possibile. Accettato e dichiarato: l'obiettivo è **caro e visibile**, non
  impossibile.
- **Stopword di default (segnale-prosa):** piccola lista built-in (keyword di linguaggio, `true`/`false`/
  `none`/`null`, estensioni comuni, `todo`/`fixme`), sovrascrivibile via `[ritual].audit_stopwords`.
- **Soglia k di default = 2** (referenziato da ≥2 punti distinti), override `[ritual].audit_threshold` o
  `--threshold`.
