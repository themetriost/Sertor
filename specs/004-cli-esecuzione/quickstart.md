# Quickstart — CLI `sertor` (esecuzione)

Riflette il design ([plan.md](plan.md)); i percorsi sono il layout target.

## Installazione (locale, editable)

```bash
uv pip install -e .            # espone il comando `sertor` nel venv (console-script)
# equivalente: python -m sertor_cli ...
```

## Indicizzare un repository

```bash
sertor index .                          # indicizza il repo corrente
sertor index /path/al/repo --corpus production
```
Riporta n. chunk e dimensione embedding. Non tocca i file del repo. Senza provider configurato →
errore esplicito (install ≠ run: nulla parte da solo).

## Interrogare

```bash
sertor search "come si valida un input"             # testo, default dal core (k, both)
sertor search "retrieval ibrido" -k 3 --type code   # solo codice, k=3
sertor search "configurare il backend" --json       # output JSON (per agenti/script)
sertor search "Server" --full                        # testo completo invece dell'anteprima
```
Indice inesistente → errore "costruisci prima l'indice".

## Indicizzare il wiki

```bash
sertor wiki index wiki/ --corpus production
```

## Osservabilità (log visibili e appender esterni)

```bash
sertor index . -v                       # log INFO strutturati a console
sertor index . --log-json               # log come JSON
sertor index . --log-config logging.yaml  # appender esterni (file, syslog, Splunk) via dictConfig
```

Esempio `logging.yaml` (dictConfig) per inviare a Splunk via un handler dedicato:
```yaml
version: 1
disable_existing_loggers: false
handlers:
  splunk:
    class: splunk_handler.SplunkHandler
    host: ...
    port: "8088"
    token: ...
    index: sertor
loggers:
  sertor_core:
    level: INFO
    handlers: [splunk]
```

## Verifica rapida (accettazione)

| Verifica | Atteso | Criterio |
|----------|--------|----------|
| `sertor index <repo>` | report chunk+dim, exit 0 | SC-001 |
| `sertor search "<q>"` | top-k con metadati | SC-002 |
| `sertor wiki index <wiki>` | n. documenti | SC-003 |
| import/installazione | nessuna indicizzazione automatica | SC-004 |
| senza provider | operazioni bloccate con errore | SC-005 |
| 2 repo diversi | funziona senza modifiche, non distruttivo | SC-006 |
| `-v`/`--log-json`/`--log-config` | log visibili / JSON / verso appender; errori loggati | SC-007 |
