# Requisiti — Packaging distribuibile (distribuzione interim `git+url`)
<!-- Deriva da: FEAT-001 (epica sertor-cli — "CLI installabile", parte packaging/distribuzione, Must) -->
<!-- Rev. 2026-06-16: prima stesura. Decisioni utente D1 (licenza MIT + file LICENSE) e D2 (ambito = formalizzare git+url interim, NON PyPI) prese in elicitazione. -->
<!-- Rev. 2026-06-17: risolte le 4 domande aperte (DA-P1..P4). DA-P1 = versione unica allineata; DA-P2 = uv primario + pip best-effort documentato (non gate Must); DA-P3 = sertor-core SOLO dipendenza interna (contro-raccomandazione utente, implicazione tracciata in REQ-041); DA-P4 = sertor-install-kit build-validato ma esonerato dai metadati user-facing. -->

## 1. Contesto e problema (perché)

La parte **eseguibile** di FEAT-001 (entry-point `sertor`/`sertor-rag`/`sertor-wiki-tools`/`sertor-flow`,
principio install≠run) è **già consegnata** dalle feature `esecuzione` (PR #21) e `installer` (PR #22).
Resta aperta la **parte di packaging/distribuzione**, l'unica casella **Must** non chiusa dell'epica.

Stato reale verificato (sessione 2026-06-16):
- Monorepo **uv workspace** con 4 pacchetti, tutti con `[build-system] = hatchling` e wheel target
  definiti → **già buildabili**: `sertor-core` (radice, libreria + console-script `sertor-rag`/
  `sertor-wiki-tools`), `sertor` (installer, entry-point `sertor`), `sertor-install-kit` (motore
  d'installazione, stdlib-only, dipendenza interna), `sertor-flow` (installer governance, entry-point
  `sertor-flow`).
- La distribuzione **`git+url`/`uvx`** è **verificata end-to-end** (uv risolve `sertor-core`/
  `sertor-install-kit` scoprendo il workspace dal checkout git, **non** da PyPI), validata live su
  ospiti reali (Kaelen, Spike).

Quattro **incoerenze/lacune** impediscono di dichiarare il packaging "fatto":
1. **Nessun file `LICENSE`** nel repo né nei pacchetti, eppure ogni `pyproject.toml` dichiara
   `license = { text = "MIT" }` → i metadati promettono MIT ma il testo non viene spedito.
2. **Versioning** hardcoded a `0.1.0` ×4, senza strategia né allineamento.
3. **Metadati di distribuzione minimi** (mancano `urls`, `classifiers`, `keywords`, `authors`
   completi) → un consumatore non ha riferimenti (repo, licenza, compatibilità).
4. **Nessuna validazione di build/installazione**: niente prova ripetibile che `uv build` produca
   wheel valide per i pacchetti distribuibili, né che l'install pulito "a un comando" funzioni su un
   ambiente vergine; il percorso **`pip`** (oltre `uv`) non è verificato.

Il problema centrale: la **distribuzione interim `git+url`** (DA-4) funziona "per fortuna/per prova",
ma non è **formalizzata, coerente e verificata**. Questa feature la rende un percorso di prima classe.

## 2. Obiettivi e criteri di successo

Obiettivo: rendere i pacchetti Sertor **distribuibili in modo coerente e verificato** via la
**distribuzione interim `git+url`**, senza pubblicazione pubblica su PyPI (FEAT-006, Won't).

Criteri di successo (misurabili):
- **CS-1 (licenza coerente):** ogni pacchetto distribuibile ha un file `LICENSE` MIT presente nel
  sorgente **e** incluso nella wheel; **0** pacchetti con `license = MIT` nei metadati ma senza testo.
- **CS-2 (metadati completi):** ogni pacchetto distribuibile espone, nei metadati della wheel,
  almeno `name`, `version`, `license`, `authors`, `urls` (repository) e `description`; **0** campi
  obbligatori mancanti rispetto alla checklist di §5 gruppo B.
- **CS-3 (build valida):** `uv build` produce, per ogni pacchetto distribuibile, **sdist + wheel**
  senza errori; la wheel include i file attesi (package-data per `sertor`); **0** build fallite.
- **CS-4 (install pulito a un comando):** su un ambiente **vergine**, un **singolo comando** installa
  `sertor` (e separatamente `sertor-flow`) da `git+url` e rende disponibili i rispettivi entry-point;
  verificato per **≥2** percorsi: `uv`/`uvx` **e** `pip`.
- **CS-5 (documentazione):** la guida d'installazione documenta il percorso `git+url` per **entrambi**
  i gestori (`uv`/`uvx` e `pip`), con il comando esatto e i prerequisiti.
- **CS-6 (confine PyPI):** **0** artefatti/azioni di pubblicazione pubblica (upload PyPI/TestPyPI,
  token, supply-chain hardening) introdotti da questa feature.

## 3. Stakeholder e attori

- **Owner/maintainer (tu):** rilascia (tagga/committa) e installa su ospiti via `git+url`.
- **Utente installatore (team interno, futuro prossimo):** installa Sertor su un repo con un comando.
- **Ambiente vergine:** macchina/venv pulito su cui si verifica l'install (proxy del CS-1 d'epica).
- **Epica `sertor-core` (dipendenza a monte):** fornisce la libreria e i console-script veicolati.
- **CI locale:** esegue la validazione di build/install senza credenziali cloud.

## 4. Ambito

### In ambito
- **File `LICENSE` MIT** in ogni pacchetto distribuibile (e nella radice del repo) + coerenza coi
  metadati `license`.
- **Versioning e metadati di distribuzione** coerenti (`version`, `authors`, `urls`, `classifiers`,
  `keywords`, `description`) sui pacchetti distribuibili.
- **Validazione di build** (`uv build` → sdist+wheel valide) per i pacchetti distribuibili, come
  controllo **ripetibile** (test/CI locale).
- **Validazione dell'install pulito a un comando** via `git+url`, per **`uv`/`uvx`** e **`pip`**, su
  ambiente vergine; verifica che gli entry-point siano invocabili.
- **Documentazione** del percorso d'installazione `git+url` (comandi esatti, prerequisiti, i due
  gestori) nella guida esistente (`docs/install.md`).
- **Definizione esplicita** di quali pacchetti sono "distribuibili per l'utente" e quali sono
  "dipendenze interne risolte dal workspace".

### Fuori ambito
- **Pubblicazione pubblica su PyPI/TestPyPI** e hardening supply-chain (firma, provenance, SBOM):
  **FEAT-006 (Won't)**. Il design non deve precluderla.
- **Fallback/ergonomia avanzata** dell'installer (avviso target non-Python, hook Linux, multi-target
  in un colpo): **FEAT-010 (Could)**; qui si copre **solo** la verifica del percorso `pip` accanto a
  `uv`, non l'ergonomia generale.
- **Lifecycle** `upgrade`/`uninstall` degli artefatti: **FEAT-008 (Could)**.
- **Wizard di configurazione** dei provider: **FEAT-003 (Should)**.
- La **ri-specifica** di entry-point/comandi/install≠run (già consegnati da `esecuzione`/`installer`):
  invariati, non ridefiniti qui.
- **Versioning automatico/da git tag** come meccanismo: è *come* (design); qui si richiede solo la
  *coerenza* e una *strategia dichiarata*.

## 5. Requisiti funzionali (EARS)

> **Due insiemi di pacchetti (definizione, da DA-P3/P4):**
> - **Build-validati (tutti e 4):** `sertor-core`, `sertor`, `sertor-install-kit`, `sertor-flow` —
>   devono buildare (sdist+wheel) e portare LICENSE coerente. Sono il bersaglio dei gruppi A e C.
> - **User-facing (install diretto):** `sertor` e `sertor-flow` — sono il bersaglio della checklist di
>   metadati completi del gruppo B (`urls`/`classifiers`/`authors`…). `sertor-core` e
>   `sertor-install-kit` sono **dipendenze interne** (DA-P3/P4): build-validate ma esonerate dalla
>   checklist user-facing.
>
> Dove un requisito dice "distributable package" senza ulteriore specifica, si applica all'insieme
> build-validato; i requisiti di metadati user-facing (REQ-010, REQ-013) si applicano all'insieme
> user-facing.

### Gruppo A — Licenza e coerenza legale
- **REQ-001 (Ubiquitous):** *The system shall include a `LICENSE` file containing the MIT license text
  in each distributable package and at the repository root.*
- **REQ-002 (Ubiquitous):** *Each package's distribution metadata shall declare the MIT license
  consistently with the bundled `LICENSE` file.*
- **REQ-003 (Event-driven):** *When a distributable package is built, the system shall include its
  `LICENSE` file inside the produced wheel.*
- **REQ-004 (Unwanted):** *If a package declares a license in its metadata without shipping the
  corresponding license text, then the build-validation check shall fail.*

### Gruppo B — Versioning e metadati di distribuzione
- **REQ-010 (Ubiquitous):** *Each distributable package shall expose `name`, `version`, `description`,
  `authors`, `license`, and a repository URL in its distribution metadata.*
- **REQ-011 (Ubiquitous):** *The system shall apply a single aligned product version across all four
  workspace packages, bumped together and documented in one source of truth* (DA-P1: versione unica
  allineata; bump manuale documentato, semver/tag automatico = design fuori ambito).
- **REQ-012 (Ubiquitous):** *Each distributable package shall declare a `requires-python` constraint
  consistent with the project baseline (Python ≥ 3.11).*
- **REQ-013 (Optional):** *Where supported by the metadata format, each distributable package shall
  declare `classifiers` and `keywords` describing license, supported Python versions, and intended use.*
- **REQ-014 (Unwanted):** *If a required distribution-metadata field (per REQ-010) is missing from a
  distributable package, then the build-validation check shall fail.*

### Gruppo C — Validazione di build (wheel)
- **REQ-020 (Event-driven):** *When the build is run for a distributable package, the system shall
  produce both a source distribution (sdist) and a wheel without errors.*
- **REQ-021 (Event-driven):** *When the `sertor` package is built, the produced wheel shall include
  the installer's bundled non-Python assets (package-data) required at install time.*
- **REQ-022 (Ubiquitous):** *The system shall provide a repeatable build-validation check, runnable in
  the local CI without cloud credentials or network access to package indexes.*
- **REQ-023 (Event-driven):** *When build validation runs, the system shall verify that each produced
  wheel declares the expected entry-points (console-scripts) for its package.*
- **REQ-024 (Unwanted):** *If building any distributable package fails, then the build-validation check
  shall report the failing package and exit non-zero.*

### Gruppo D — Install pulito "a un comando" (verifica)
- **REQ-030 (Event-driven):** *When a user installs `sertor` from `git+url` into a clean environment
  with a single command, the system shall make the `sertor` entry-point available without manual
  additional steps.*
- **REQ-031 (Event-driven):** *When a user installs `sertor-flow` from `git+url` into a clean
  environment with a single command, the system shall make the `sertor-flow` entry-point available.*
- **REQ-032 (Event-driven):** *When `sertor`/`sertor-core` is installed from `git+url`, the system
  shall resolve its workspace dependencies (`sertor-core`, `sertor-install-kit`) from the git checkout
  without requiring a public package index.*
- **REQ-033 (Ubiquitous):** *The system shall verify the clean single-command install for at least two
  package managers: `uv`/`uvx` and `pip`.*
- **REQ-034 (Event-driven):** *When the clean install completes, the system shall verify that each
  installed entry-point is invocable (e.g., responds to a help/version invocation) returning success.*
- **REQ-035 (Unwanted):** *If the clean single-command install fails to provide a declared entry-point
  via `uv`/`uvx` (the primary path), then the verification shall fail and identify the package and
  package manager.* (DA-P2: `uv`/`uvx` è il percorso primario e gate; `pip` è verificato ma, se non
  risolve le dipendenze di workspace da `git+url`, il limite è **documentato** e l'ergonomia piena di
  `pip` è rinviata a FEAT-010 — il `pip`-workspace **non** blocca il "done" del Must.)

### Gruppo E — Documentazione del percorso d'installazione
- **REQ-040 (Ubiquitous):** *The installation guide shall document the exact `git+url` install command
  for both `uv`/`uvx` and `pip`, including prerequisites.*
- **REQ-041 (Ubiquitous):** *The installation guide shall state that the user-facing install
  entry-points are `sertor` and `sertor-flow`, and that `sertor-core` (and `sertor-install-kit`) are
  internal dependencies resolved from the workspace — not advertised as a direct user install.* (DA-P3:
  `sertor-core` resta dipendenza interna; i suoi console-script `sertor-rag`/`sertor-wiki-tools` sono
  raggiungibili **dopo** `sertor install`, non promossi come percorso `uvx --from` diretto. Implicazione
  della scelta utente contro-raccomandazione: esporli come install diretto sarà un'aggiunta futura
  non-breaking, non parte di questo ambito.)
- **REQ-042 (Ubiquitous):** *The documentation shall state explicitly that public PyPI publication is
  out of scope (deferred to FEAT-006) and that `git+url` is the interim distribution channel.*

### Gruppo F — Invarianti preservati
- **REQ-050 (Unwanted):** *If a package is installed, then the system shall not start RAG ingestion or
  index creation (install ≠ run).*
- **REQ-051 (Ubiquitous):** *The packaging and its verification shall not require, embed, or persist
  any secret (e.g., API keys) in version-controlled files or in built artifacts.*
- **REQ-052 (Event-driven):** *When build/install verification runs against a host repository, the
  system shall not overwrite user-modified files.*
- **REQ-053 (Ubiquitous):** *The packaging shall remain host-agnostic: building/installing shall not
  assume a specific host repository, language distribution, or operating system beyond the declared
  prerequisites.*

## 6. Requisiti non funzionali

- **NFR-1 (ripetibilità):** la validazione build/install è **deterministica** e ripetibile in CI
  locale, senza rete verso indici di pacchetti pubblici (per la build) e senza credenziali cloud.
- **NFR-2 (isolamento):** la verifica dell'install pulito avviene in un **ambiente isolato** (venv/env
  effimero), così da non dipendere dallo stato della macchina di sviluppo.
- **NFR-3 (non-regressione):** l'introduzione di metadati/LICENSE non altera il comportamento runtime
  dei pacchetti già su master (entry-point, import, suite test esistente verde).
- **NFR-4 (manutenibilità):** la strategia di versioning è dichiarata in un unico punto di verità ed è
  applicabile senza editing manuale disallineato tra i 4 pacchetti.
- **NFR-5 (portabilità doc):** la guida d'installazione resta valida per ospiti diversi (non cita
  percorsi specifici di una sola macchina).

## 7. Vincoli, assunzioni e dipendenze

**Vincoli**
- **Licenza = MIT** (decisione utente D1), coerente con SpecKit MIT già vendorato da `sertor-flow`.
- **Distribuzione interim = `git+url`** (DA-4); PyPI fuori ambito (FEAT-006).
- **Python ≥ 3.11**; gestori supportati: **`uv`/`uvx`** (preferito) e **`pip`**.
- Coerenza con **DA-8** (`sertor` = installer; `sertor-rag`/`sertor-wiki-tools` = esecuzione, console-
  script di `sertor-core`; `sertor-flow` = governance) e con **install≠run** (REQ-E2 d'epica).

**Assunzioni**
- I 4 pacchetti restano in **uv workspace**; `sertor-core` e `sertor-install-kit` sono risolti dal
  workspace via `git+url`, non pubblicati separatamente.
- La build resta su **hatchling** (già configurata); questa feature non cambia il backend di build.
- L'ambiente vergine di verifica ha accesso di rete a **GitHub** (per `git+url`) ma **non** a PyPI per
  i pacchetti Sertor.

**Dipendenze**
- A monte: `sertor-core` (libreria + console-script) e `sertor-install-kit` (dipendenza interna).
- Documentazione: `docs/install.md` (esistente) come sede della guida.
- Collegata (non assorbita): **FEAT-010** (ergonomia/portabilità installer); **FEAT-006** (PyPI).

## 8. Rischi

- **R-1 — Risoluzione workspace fragile via `git+url`:** un cambio di layout del monorepo potrebbe
  rompere la scoperta del workspace dal checkout git (oggi funziona, REQ-032). *Mitigazione:* verifica
  in CI su ambiente vergine.
- **R-2 — Divergenza `pip` vs `uv`:** `pip` potrebbe non risolvere le dipendenze di workspace come
  `uv`. *Mitigazione:* REQ-033 verifica entrambi; se `pip` non regge il workspace, documentare il
  limite e rimandare l'ergonomia a FEAT-010 (domanda aperta DA-P2).
- **R-3 — Package-data mancanti nella wheel:** asset dell'installer esclusi dal build → install rotto.
  *Mitigazione:* REQ-021/REQ-023 li verificano esplicitamente.
- **R-4 — Scope creep verso PyPI:** introdurre token/CI di pubblicazione viola il confine. *Mitigazione:*
  CS-6 + REQ-042.
- **R-5 — Versioni disallineate** tra i 4 pacchetti → install incoerenti. *Mitigazione:* REQ-011 +
  NFR-4 (strategia unica dichiarata).

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001..004, REQ-010, REQ-011, REQ-012, REQ-014, REQ-020..024, REQ-030..035, REQ-040, REQ-041, REQ-042, REQ-050, REQ-051, REQ-053 | Coerenza legale + metadati essenziali + build valida + install pulito verificato (uv & pip) + doc + invarianti: è il nucleo che rende il packaging "fatto" per la distribuzione interim. |
| **Should** | REQ-013 (classifiers/keywords), REQ-052 (non-sovrascrittura in verifica su host) | Migliorano qualità dei metadati e sicurezza della verifica, ma non bloccano il "done". |
| **Could** | — | (Ergonomia pip/multi-target → FEAT-010.) |
| **Won't** | Pubblicazione PyPI/TestPyPI, firma/provenance/SBOM, versioning automatico da tag come meccanismo | FEAT-006 / materia di design. |

## 10. Decisioni (ex domande aperte — risolte 2026-06-17)

- **[DA-P1 — Strategia di versioning] → RISOLTA: versione unica allineata.** Un'unica versione di
  prodotto per tutti e 4 i pacchetti, bumpata insieme e documentata in un solo punto di verità (REQ-011,
  NFR-4). semver/tag automatico legato ai merge = *design*, fuori ambito.
- **[DA-P2 — `pip` e workspace] → RISOLTA: `uv`/`uvx` primario, `pip` best-effort documentato.**
  `uv`/`uvx` è il percorso primario e il gate del Must (REQ-035). `pip` è comunque verificato (REQ-033);
  se `pip install git+url#subdirectory=…` non risolve le dipendenze di workspace come `uv`, il **limite
  è documentato** e l'ergonomia piena di `pip` è rinviata a **FEAT-010** — il caso pip-workspace **non**
  blocca il "done".
- **[DA-P3 — `sertor-core` come pacchetto user-facing] → RISOLTA (contro-raccomandazione): solo
  dipendenza interna.** `sertor-core` (e `sertor-install-kit`) restano dipendenze interne risolte dal
  workspace, **non** promosse come install diretto dell'utente. I console-script `sertor-rag`/
  `sertor-wiki-tools` sono raggiungibili **dopo** `sertor install` (REQ-041). *Implicazione tracciata:*
  esporli come percorso `uvx --from` diretto sarà un'aggiunta futura non-breaking, non parte di questo
  ambito.
- **[DA-P4 — `sertor-install-kit` distribuibile?] → RISOLTA: build-validato, metadati esonerati.** Se
  ne valida la **build** (deve buildare per essere risolto dal workspace, REQ-020/022/024), ma è
  **esonerato** dalla checklist di metadati user-facing (`urls`/`classifiers`/`authors` completi) perché
  è dipendenza interna senza entry-point. Vale lo stesso per `sertor-core` quanto alla porta d'ingresso
  (DA-P3), pur restando per esso utile un set di metadati per chiarezza.
