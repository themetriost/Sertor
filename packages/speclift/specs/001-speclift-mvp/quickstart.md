# Quickstart — SpecLift MVP

> Stato: MVP in costruzione. Lo stadio di stesura EARS è **stubbed** finché la modalità bundle-driven di
> `requirements` non è disponibile in Sertor; il resto della pipeline è reale ed end-to-end.

## Prerequisiti

- Python 3.12+
- `git` su PATH
- **Sertor RAG configurato e indicizzato** nel progetto target (`uv run --project .sertor sertor-rag
  doctor` verde). SpecLift usa il RAG via vehicle; se il RAG non è disponibile, fallisce *loud*.

## Installazione (dev)

```bash
# dalla radice del progetto
uv venv && uv pip install -e .       # installa la CLI `speclift`
pytest                                # esegue la suite (core deterministico con fake)
```

## Uso

```bash
speclift HEAD                         # genera il report dal commit HEAD (JSON + Markdown)
speclift --staged --format md         # dal diff staged, vista Markdown a schermo
speclift --range main..HEAD --out ./report
```

## Cosa ottieni

- `*.speclift.json` — output canonico (conforme a `contracts/output.schema.json`): requisiti EARS
  multi-quota, ognuno con la sua àncora **verificata**, più i `drifts` proposti e gli `excluded`
  (requisiti scartati per àncora non verificabile — trasparenza del moat).
- `*.speclift.md` — vista leggibile, derivata e **coerente** col JSON.

## Limiti noti (MVP)

- Stesura EARS *stubbed* (placeholder ancorati) finché Sertor non offre la modalità bundle-driven.
- "Il test tocca il simbolo" = referenza statica (no esecuzione dei test).
- Consumatori a valle (SpecAudit/Debrief), MCP e gate di CI: fuori scope.
