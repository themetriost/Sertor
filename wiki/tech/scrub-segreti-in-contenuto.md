---
title: Scrub dei segreti nel contenuto testuale libero
type: tech
tags: [privacy, scrub, secrets, redazione, contenuto, feat-001, osservabilita, sicurezza]
created: 2026-06-14
updated: 2026-06-14
sources: ["src/sertor_core/observability/scrub.py", "src/sertor_core/observability/logging.py", "src/sertor_core/services/memory_archive.py"]
---

# Scrub dei segreti nel contenuto testuale libero

La [[memoria-conversazioni|memoria episodica]] cattura i transcript interi. I transcript contengono conversazioni libere, e chiunque lavora con un progetto incolla accidentalmente segreti (chiavi API, token di autorizzazione, password) nella chat. Questa pagina descrive come il sistema li ripulisce.

## Il problema

I **transcript sono il dato più sensibile del sistema**: contengono codice proprietario, decisioni, segreti incollati per errore. Se archiviati in chiaro, sono una **breccia di sicurezza**.

Opzioni:
1. **Non archiviarli** → ma allora perdi la fonte grezza, non puoi fare ricerca episodica, non puoi ritornare al contesto.
2. **Archiviarli in chiaro** → breccia.
3. **Archiviarli ripuliti** → privacy-by-default, ma devi riconoscere i segreti.

Sertor sceglie l'opzione 3: **scrub defensivo** dei pattern noti prima di persistere.

## Due livelli di scrub

### Livello 1: Scrub per-campo (logging)

Esiste già in `observability/logging.py` (`redact` function): quando emetti un evento strutturato via `log_event`, i campi con nomi che contengono hint di segreto (key, token, secret, password) sono redatti prima dell'emission.

Esempio:
```python
log_event("embeddings", {
    "operation": "embed",
    "api_key": "sk-...",  # redacted in event
    "texts": [...],
})
```

Output: il campo `api_key` non compare in chiaro, viene sostituito con `***REDACTED[api_key]***`.

### Livello 2: Scrub nel contenuto libero (FEAT-001)

Il contenuto del transcript è **testo libero non-strutturato**: non ha campi predefiniti. Uno ne incolla una chiave API, la mette nel messaggio di chat, e il transcript la contiene come parte del testo.

Entra in gioco `scrub_text` in `observability/scrub.py` (67 righe): pattern-based regex-driven scrub che:

1. **Riconosce i pattern noti**: API key (es. `sk-…`), token bearer, assegnamenti `KEY=VALUE` con hint di segreto nel nome della chiave, header Authorization.
2. **Sostituisce con segnalatori**: `sk-abc123…` → `[REDACTED: OpenAI_api_key]`.
3. **Ripiego conservativo**: se un pattern fallisce o è ambiguo, redige l'intero segmento.
4. **Configurabile**: nuovi pattern possono essere aggiunti via manopola senza toccare il codice.

## Implementazione

### Funzione pura `scrub_text(text: str) -> str`

Input: testo libero (eventualmente con segreti).  
Output: testo scrubbed (segreti redatti).

Logica:
1. Per ogni pattern configurato, scandisci il testo con regex.
2. Se match, sostituisci il valore con il segnalatore (es. `[REDACTED: api_key]`).
3. Se la substituzione fallisce (exception regex, etc), redigi l'intera sottostinga → fallback conservativo.
4. Emetti warning per ogni redazione (osservabilità).

### Pattern coperti (default)

1. **OpenAI API keys**: `sk-[A-Za-z0-9\-]*` → `[REDACTED: openai_api_key]`.
2. **AWS access keys**: `AKIA[0-9A-Z]{16}` → `[REDACTED: aws_access_key]`.
3. **Bearer tokens**: `bearer\s+[^\s]+` → `[REDACTED: bearer_token]`.
4. **Assegnamenti chiave-valore con hint**:
   - Pattern: `(api_key|token|secret|password|authorization|auth_token)\s*=\s*([^\s,;\n]+)`
   - Match: `API_KEY=sk-123` → sostituisci.
5. **Header Authorization inline**: `Authorization:\s*[^\n]+` → `[REDACTED: auth_header]`.

### Configurazione

Manopola `SERTOR_MEMORY_SCRUB_PATTERNS` in `Settings` (lista di dict):

```python
[
    {"name": "openai", "pattern": r"sk-[A-Za-z0-9\-]*", "label": "openai_api_key"},
    {"name": "aws", "pattern": r"AKIA[0-9A-Z]{16}", "label": "aws_access_key"},
    # ...custom patterns per il progetto...
]
```

Se non configurato, usa i pattern default. Aggiungere pattern non richiede modifica al core.

### Garanzie

- **Mai bypassabile**: lo scrub è sempre applicato se SERTOR_MEMORY=true (non c'è flag per disattivarlo).
- **Conservativo**: se incerto, redige. Meglio perdere informazione che lasciar passare un segreto.
- **Osservabile**: ogni redazione emette un warning strutturato (metrica di "quanti segreti trovati oggi").

## Integrazione

### Nel servizio di archiviazione

`MemoryArchiveService` chiama `scrub_text` su ogni turnazione prima di passarla al store:

```python
for turn in content.turns:
    scrubbed_turn = TranscriptTurn(
        index=turn.index,
        role=turn.role,
        text=scrub_text(turn.text),  # scrubbed
        ts=turn.ts
    )
    # ... persisti scrubbed_turn
```

### Negli eventi di osservabilità

Quando FEAT-001 emette eventi `memory_session_archived`, il contenuto è già scrubbed (il servizio lo scrub prima di persistere). Se necessario emettere metriche di scrub (quante redazioni), l'evento `memory_session_archived` porta un campo `redactions_count`.

## Limitazioni note

1. **Pattern non riconosciuto**: un segreto in un formato non nel config passa in chiaro → dipende dalla completezza del config e dalla vigilanza.
2. **Segreto a cavallo di due turni**: se uno split-line il secret tra due messaggi, il regex non lo riconosce → unlikely ma possibile.
3. **Costo**: lo scrub con regex è sincrono e lineare; su transcript enormi (sessioni di ore) è visibile ma trascurabile (O(n) nel testo).

## Confronto: redazione per-campo vs redazione contenuto

| Aspetto | Per-campo (`logging.py`) | Contenuto (`scrub.py`) |
|---------|--------------------------|------------------------|
| **Input** | Campo strutturato (chiave-valore) | Testo libero non-strutturato |
| **Trigger** | Nome del campo contiene hint | Pattern regex nel testo |
| **Sostituto** | `***REDACTED[field]***` | `[REDACTED: pattern_name]` |
| **Usato dove** | Eventi strutturati (`log_event`) | Transcript, contenuto testo |
| **Fallback** | Nessuno (field è esterno, non dentro il valore) | Conservativo: redigi l'intero segmento |

Entrambi sono **parte dello stesso principio**: no segreti mai, gratis.

## Stato

- ✅ **Scrub per-campo**: esistente (pre-FEAT-001), in `observability/logging.py`.
- ✅ **Scrub contenuto**: implementato in FEAT-001 (PR #45), in `observability/scrub.py`.
- 📋 **Config pattern per-progetto**: manopola + test (FEAT-001 done).
- 📋 **Metriche di scrub**: quanti segreti trovati per periodo (future, osservabilità).

---

## Pagine collegate

- [[memoria-conversazioni]] — il contesto (archivio episodico che usa questo scrub).
- [[transcript-capture-adapter-e-storage]] — dove viene applicato (nel servizio `MemoryArchiveService`).
- [[feat-001-memoria-cattura-archiviazione]] — feature che lo introduce.
