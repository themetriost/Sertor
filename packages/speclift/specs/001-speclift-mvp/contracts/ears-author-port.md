# Contract — `EarsAuthor` port (delega della stesura EARS)

L'**unico** stadio LLM. SpecLift NON formula EARS in proprio: la stesura è a carico
dell'**agente chiamante** (l'assistente host che guida la skill, dentro **Sertor Flow**) — decisione
2026-06-29, che **disambigua** la clarify 2026-06-26.

> **Storia della decisione.** La clarify del 2026-06-26 diceva "delega alla capacità `requirements` di
> Sertor in modalità *bundle-driven non interattiva*". Corretto nello spirito (SpecLift esce **dentro
> Sertor Flow**), ma ambiguo: era stato letto come *un programma batch separato di Sertor*, e
> implementato come dipendenza esterna inesistente → stadio bloccato (BLOCKED-EXT). Disambiguazione: in
> Sertor Flow l'intelligenza È **l'agente chiamante**. Quindi "lo fa Sertor" = "lo fa l'agente che opera
> la skill di Sertor Flow". Niente batch esterno; **niente BLOCKED-EXT**.

Questo contratto isola il core dall'autore (Principio I/II): chiunque scriva le frasi — agente
chiamante (produzione) o stub deterministico (test/offline) — il **moat deterministico** (verify) è ciò
che rende l'output onesto.

## Interfaccia (port)

```text
EarsAuthor.author(bundle: EvidenceBundle) -> EarsAuthoringResult

EarsAuthoringResult = {
  requirements: list[EarsRequirement],   # su tutte e tre le quote per gli elementi rilevanti
  open_questions: list[str],             # lacune che la modalità non interattiva non chiude
}
```

### Invarianti (vincolanti)
- **Nessuna àncora nuova**: ogni `requirement.anchor` DEVE essere un'àncora già presente in `bundle`
  (REQ-X01). L'adapter rifiuta/segnala output che introduce àncore non nel bundle.
- **Non interattivo**: nessuna domanda all'utente in tempo reale; ciò che non è determinabile finisce in
  `open_questions`.
- **Multi-quota**: per ogni `EvidenceItem` rilevante, requisiti su `user_capability`, `behaviour`,
  `implementation`; una quota priva di requisito è segnalata, non omessa.
- **Formato EARS standard**: la notazione è quella della capacità `requirements` (fonte di verità unica).
- **Fail-loud**: se la capacità `requirements` non è disponibile → `EarsAuthorUnavailableError`; nessun
  generatore interno di ripiego.

## Realizzazione: agente chiamante via skill sottile (no batch esterno)

L'autore non è un callable in-process: è l'**agente chiamante**. La pipeline si spezza quindi al confine
del bundle, orchestrata dalla **skill sottile**:

1. **CLI — emetti il fascicolo** (deterministico): ingest → parse → locate → bundle → **stop**. Output:
   l'`EvidenceBundle` (i fatti, già ancorati).
2. **Agente — scrivi le frasi**: legge il bundle e produce i requisiti EARS multi-quota, ognuno agganciato
   a un'**àncora già presente nel bundle**. Rispetta le invarianti qui sopra.
3. **CLI — verifica & render** (deterministico): riprende i requisiti dell'agente, **verifica le àncore
   sul filesystem (il moat)** e stampa. Un'àncora inventata o non verificabile è **rifiutata/esclusa**,
   non corretta in silenzio.

Il `lift` deterministico fa già rispettare REQ-X01 ("nessuna àncora nuova"): è il guardiano che tiene
onesto qualunque autore, agente compreso.

### `StubEarsAuthor` — solo test/offline (NON la via di produzione)
L'adapter `ears_requirements.py` resta come **stub deterministico** per i test e per l'uso offline (CLI
senza agente): per ogni `EvidenceItem` emette tre placeholder ancorati al bundle + una `open_question`
che dichiara "stesura demandata all'agente chiamante". Serve a esercitare verify/render end-to-end senza
un agente; **non** è il percorso con cui SpecLift produce requisiti reali.

> **Implicazione (onestà):** la CLI **da sola** non emette requisiti veri (solo placeholder). La capacità
> piena è *CLI + skill + agente* insieme — coerente con la decisione "CLI + skill sottile".
