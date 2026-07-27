# Quickstart — verificare l'ancora derivata dal vivo

**Feature**: `123-feat-045-ancora-derivata-scan`

> **Perché queste prove esistono.** Tre volte in tre giorni la prova dal vivo ha colto ciò che i test
> non vedevano (v0.3.1, il comando d'upgrade). E la modalità **non-git** è **irraggiungibile sul nostro
> nodo** — siamo un repo — quindi le sue prove sono su **fixture**, non su osservazione: è il terzo
> limite di [[dogfood-fidelity]] preso sul serio invece che a parole.

Tutti i comandi in **PowerShell**.

---

## 1. Il caso che oggi fallisce (US1 — il deadlock)

La sequenza reale che nessuna sessione riesce a chiudere:

```powershell
uv run --project .sertor sertor-wiki-tools scan --json   # prima del merge
gh pr merge <n> --merge --delete-branch
git checkout master; git pull
uv run --project .sertor sertor-wiki-tools scan --json   # DOPO
```

**Atteso dopo il fix:** `pending: 0`, `anchor_kind: "git"`, `anchor_ref` = la consegna che ha portato
la voce di giornale.
**Oggi:** l'esito dipende da quale file git ha scritto per ultimo — cioè è una lotteria.

## 2. La prova che conta davvero: il determinismo (SC-002)

La prima prova mostra che *funziona*; questa mostra che **non dipende dagli orologi**, che è il vero
requisito:

```powershell
$before = uv run --project .sertor sertor-wiki-tools scan --json
Get-ChildItem -Recurse src, specs, requirements, wiki/log -File |
    ForEach-Object { $_.LastWriteTime = Get-Date }        # tutti gli orologi ad "adesso"
$after = uv run --project .sertor sertor-wiki-tools scan --json
if ($before -eq $after) { "DETERMINISTICO" } else { "REGRESSIONE: l'orologio conta ancora" }
```

Oggi questo confronto **fallisce**. È la differenza fra «ha funzionato» e «è corretto».

## 3. Il file ignorato non blocca più (US2 / FEAT-048)

```powershell
"scratch" | Out-File .venv/SCRATCH.md         # .venv/ è gitignorato
uv run --project .sertor sertor-wiki-tools scan --json   # atteso: NON conta
Remove-Item .venv/SCRATCH.md
```

*(Già verificato in fase di design: `git status --porcelain` non lo vede — `research.md` R3.)*

## 4. I file sono nominati (US2)

```powershell
"x = 1" | Out-File src/sertor_core/_probe.py
uv run --project .sertor sertor-wiki-tools scan --json
Remove-Item src/sertor_core/_probe.py
```

**Atteso:** `pending_paths` contiene `src/sertor_core/_probe.py`, e il **messaggio** lo nomina.
Oggi direbbe solo «1 file».

## 5. La voce stantia è nominata, e non vale (FR-004a)

```powershell
"nota" | Add-Content wiki/log/2026-07-24.md    # partizione di un ALTRO giorno, non consegnata
"y = 2" | Out-File src/sertor_core/_probe2.py
uv run --project .sertor sertor-wiki-tools scan --json
git checkout wiki/log/2026-07-24.md; Remove-Item src/sertor_core/_probe2.py
```

**Atteso:** `pending: 1` (**blocca**, la voce non è di oggi) **e** `stale_recording:
"wiki/log/2026-07-24.md"` — così chi riceve il blocco capisce perché un giornale «già modificato» non
è bastato. Senza questo campo la diagnosi tornerebbe a essere un'indagine.

## 6. Il gate si soddisfa in un turno, senza committare (FR-004)

```powershell
"z = 3" | Out-File src/sertor_core/_probe3.py
uv run --project .sertor sertor-wiki-tools scan --json      # atteso: pending >= 1
uv run --project .sertor sertor-wiki-tools append-log --entry-op record --title "prova"
uv run --project .sertor sertor-wiki-tools scan --json      # atteso: pending 0, SENZA commit
git checkout wiki/log; Remove-Item src/sertor_core/_probe3.py
```

Se questo caso fallisse, il gate pretenderebbe una consegna per potersi soddisfare: **un deadlock
nuovo al posto di quello vecchio**.

## 7. L'ospite non-git — su fixture, non qui (US3, Principio XIII)

**Non eseguibile sul dogfood.** Serve una cartella che **non** sia un repo:

```powershell
$h = Join-Path $env:TEMP "sertor-nogit-fixture"
New-Item -ItemType Directory -Force $h | Out-Null
# …struttura wiki minima + wiki.config.toml + un file sotto src/…
uv run --project .sertor sertor-wiki-tools scan --config $h/wiki.config.toml --root $h --json
```

**Atteso:** funziona come oggi, `anchor_kind: "mtime"`, `anchor_fallback_reason:
"not_a_repository"` — **dichiarato, non taciuto**. Aggiungere anche la fixture `log_never_committed`
(cartella *che è* un repo ma senza il giornale consegnato).

## 8. La guardia che protegge il gate (FR-012)

```powershell
uv run pytest packages/sertor/tests/test_scan_schema_frozen.py -q
```

Deve asserire che la stringa emessa da `scan` è **letteralmente** quella confrontata dagli hook,
leggendo **entrambe le fonti**. Se un giorno qualcuno bumpasse lo schema, il gate non si romperebbe:
**sparirebbe** — ed è per questo che la guardia va scritta **prima** del resto (fase 2 del piano).

## 9. Non-regressione (Principio X)

```powershell
uv run pytest tests/unit/test_wiki_tools_scan.py tests/unit/test_ritual_check.py -q
```

Devono passare **senza essere modificati**. Se servisse toccarli, non sarebbe un aggiornamento: sarebbe
il segnale che il comportamento è cambiato dove non doveva.
