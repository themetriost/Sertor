# Contract — Provider locali `hash` e `glove` (REQ-010..024, 030..035, 040/041)

Entrambi implementano la porta `EmbeddingProvider` (structural typing): `name:str`, `dim:int|None`,
`batch_size:int`, `embed(texts)->list[list[float]]`. La porta **NON cambia** (REQ-050).

---

## `HashingEmbedder` — pavimento zero-download (Gruppo B)

| Proprietà | Contratto |
|-----------|-----------|
| Identità | `name == "hash:512"`, `dim == 512` (REQ-012) |
| Dipendenze | **sola stdlib** (`hashlib`, `math`); nessun extra, nessuna rete, nessuna credenziale (REQ-010) |
| Vettore | char-n-gram `n∈{3,4,5}` (lowercase, padding ai confini) → `blake2b(digest_size=8)` → sign-hashing su `dim` → accumulo → **L2-norm** (REQ-011) |
| Determinismo | identico testo → identico vettore cross-run/macchina/Python (no `hash()` salted) (REQ-013) |
| OOV / identificatori | i char-n-gram fanno contribuire segnale anche a token fuori da ogni vocabolario (REQ-011) |
| Testo vuoto | vettore zero (deterministico); nessun fallimento |
| Avviso | provider attivo → `WARNING` «ricerca NL limitata; configura glove/ollama/azure» (REQ-014) |

### Test (FIRST, offline)
- `embed(["x"]) == embed(["x"])` e dimensione 512 per ogni vettore.
- stesso vettore con `PYTHONHASHSEED` diverso (subprocess) — determinismo cross-Python.
- token identificatore OOV (`build_indexer`) → vettore non nullo.
- testo vuoto → vettore di 512 zeri.

---

## `GloveEmbedder` — vettori statici, default (Gruppo C/D/E)

| Proprietà | Contratto |
|-----------|-----------|
| Identità | `name == "glove:300"`, `dim == 300` (REQ-022) |
| Sorgente vettori | `glove.6B.300d.txt` (GloVe 6B 300d, PDDL), **nessun modello eseguito** (REQ-020) |
| Vettore | media dei vettori dei token in-vocab → **L2-norm** (REQ-021) |
| OOV | split camelCase/snake_case poi retry; ancora OOV → scartato; tutto-OOV → vettore zero (REQ-023) |
| Dipendenze | solo il file dati + `numpy` **lazy** (già transitiva); selezionare altro provider non lo importa né scarica (REQ-024/053) |
| Caricamento | **lazy alla prima `embed`** (install≠run) |

### Acquisizione & cache (Gruppo D)
| Caso | Comportamento |
|------|---------------|
| `SERTOR_GLOVE_PATH` impostato ed esistente | usa quel file, **nessun download** (REQ-032) |
| file in cache utente condivisa | riusa, **nessun download** (REQ-035) |
| prima indicizzazione, file assente | **scarica** `glove.6B.zip` + avviso una-tantum (~822 MB), estrae 300d (REQ-030/033) |
| `install` / `search` con cache presente | **nessun download** (acquisizione legata all'indicizzazione, REQ-034) |
| dir cache | `%LOCALAPPDATA%\sertor\glove` (Win) · `$XDG_CACHE_HOME`/`~/.cache/sertor/glove` (REQ-031) |

### Fail-loud (Gruppo E, Principio XII)
| Caso | Esito |
|------|-------|
| file assente, no path, no rete | `GloveUnavailableError` azionabile che nomina **entrambe** le vie d'uscita (`SERTOR_GLOVE_PATH`, `SERTOR_EMBED_PROVIDER=hash`) (REQ-040) |
| download/caricamento/parse fallito | errore **esplicito**, **nessun** fallback silenzioso ad altro provider (REQ-041) |

### Test (FIRST, offline — file GloVe finto/minuscolo come fixture)
- `embed` con vocabolario fixture (2-3 token) → media+norm deterministica.
- OOV `getUserId` → split camel → vettori sotto-token; tutto-OOV → zero.
- override path → mai download (monkeypatch del downloader → asserzione "non chiamato").
- file assente + downloader che solleva (no-rete) → `GloveUnavailableError` con entrambe le vie.
- cache presente → `glove_cache_hit` emesso, downloader non chiamato.

---

## Osservabilità comune (REQ-042, metrics-only)
`embeddings_provider_selected` (provider chiuso), `glove_download` (size_mb, source_host),
`glove_cache_hit` (bool). Nessun segreto, nessun path con username, nessun testo di query.
