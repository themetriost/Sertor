# Contract — Regole di stile (ALL-CAPS, ToC, wikilink)

Contratto deterministico applicato dalla pulizia e verificato dalle guardie. Non cambia la semantica.

## R1 — ALL-CAPS enfatico
- **Dominio:** body in prosa + campo `description:` del frontmatter degli asset A1–A5.
- **Match (giudizio, esaustivo):** parola intera A–Z, ≥2 lettere, usata come enfasi in prosa.
- **Esclusioni:** (a) code span `` `...` ``; (b) fenced block ```` ``` ````; (c) output CLI citato;
  (d) allowlist `RAG CLI MCP API JSON JSONL YAML TOML URL NL POSIX HTTP SDLC MRR STOP PASS FAIL PATH`
  (+ `EARS FEAT REQ` in A5).
- **Trasformazione:** `**bold**` se l'enfasi è load-bearing, altrimenti minuscolo. La regola/why
  associata resta nella stessa frase o adiacente.
- **Enforcement (guardia):** sottoinsieme `[A-Z]{4,}` post-strip, meno allowlist, deve essere ∅.
- **Conversioni note (riferimento, non esaustivo per ≤3 lettere):**
  - A1: `ONLY`→only · `MANDATORY`→**required** (o **always**) · `EVERY`→every · `WITHOUT`→without ·
    `do NOT`→do not/**never**.
  - A2: `DERIVES`→derives · `ONLY`→only · `BUILD`→build · `ASSISTED`→**assisted** · `DETERMINISTIC`→
    **deterministic** · `DOES NOT`→does not · `DATA`→data · `NAVIGATION`→navigation · `DISCOVER`→
    discover · `EMPTY`→empty · `SHOULD`→should.
  - A3: `OFFER`→offer · `WAS`→was · `NOT`→not.
  - A4: `SAME`→**same** · `JUDGMENT`→**Judgment** (nella frase «**Judgment** is left to you»).
  - A5: `SEMPRE`→sempre (lingua IT invariata; `EARS` preservato).

## R2 — Table of Contents (solo A4)
- Posizione: immediatamente dopo il blockquote introduttivo, prima di `## 0.`.
- Forma: heading `## Contents` + lista markdown di 8 voci `- [§N — <titolo>](#<anchor>)`.
- Anchor: slug GitHub della heading **reale** (vedi `data-model.md` §3). Solo §0–§7 (no subsection).
- Vincolo: nessuna heading/contenuto di sezione esistente viene rinominato o spostato.

## R3 — Wikilink orfano (solo A4)
- Rimuovere l'intera frase «See `[[assistant-targeting]]` for the targeting mechanism.» (riga ~52).
- Nessun nuovo riferimento introdotto; il capoverso resta self-contained.
- Invariante: dopo strip dei code span, **zero** occorrenze di `[[` in A1–A4.

## R4 — «How to invoke» pointer (A2, A3) — DA-1/FR-010
- Sostituire il blockquote `> **How to invoke `sertor-rag`.** …` con il pointer di `data-model.md` §4.
- Closure-safe: il target `sertor-cli-reference.md` è depositato dal piano RAG (FEAT-021) dove citato.
- Non re-introdurre né espandere «How to invoke» in altri body (RNF-5).

## R5 — Condensazione sezioni (DA-D-5)
- A1: rimuovere la sezione «What NOT to do» (tutti gli item duplicano regole inline — vedi mapping in
  `stable-substrings.md`); ogni regola sopravvive inline (pin).
- A2: «What NOT to do» → tenere «never write secrets» e «do not invent paths»; rimuovere «do not run
  the evaluation on the user's behalf» (duplica Purpose + Hard boundary «No execution»).
- A3: «What NOT to do» → piegare l'unico item unico («do not write secrets») come bullet della «Hard
  boundary (no implicit judgment)»; rimuovere la heading.
- Vincolo trasversale: nessuna regola **unica** eliminata (FR-005); solo duplicati verbatim/semantici.
