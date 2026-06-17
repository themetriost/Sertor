# Quickstart — `sertor configure`

**Feature**: 051-configurazione-wizard · **Branch**: `051-configurazione-wizard`

Porta la configurazione del RAG da «segreti vuoti» a «pronta» con un comando guidato, senza aprire un
editor. Vive nell'installer `sertor` (`packages/sertor`). Non avvia mai l'indicizzazione (install≠run).

---

## Prerequisiti

- Sertor installato come strumento (es. `uvx --from "git+…#subdirectory=packages/sertor" sertor`).
- Tipicamente dopo `sertor install rag` (che lascia `.sertor/.env` con i segreti vuoti) — ma `configure`
  funziona **anche** senza, creando `.sertor/.env` dal template (FR-015).

---

## 1. Wizard interattivo (profilo Azure)

```powershell
sertor configure --backend azure
```

Con un terminale interattivo, il comando chiede uno per uno i campi mancanti (endpoint, API key —
nascosta —, deployment), mostrando nome, descrizione e valore corrente mascherato. Al termine:

```
Profilo: azure (embedding) + local (store)
Campi: AZURE_OPENAI_ENDPOINT=set, AZURE_OPENAI_API_KEY=set (****3f2a), AZURE_OPENAI_EMBED_DEPLOYMENT=kept
Validazione: completa ✔
Scritto in .sertor/.env
```

Exit `0`. Ora `sertor-rag index .` può partire.

---

## 2. Non interattivo / CI (nessun prompt)

```powershell
# i segreti via ambiente (preferito in CI); i non-segreti via --set
$env:AZURE_OPENAI_API_KEY = "…"
sertor configure --backend azure `
  --set AZURE_OPENAI_ENDPOINT=https://my.openai.azure.com/openai/v1 `
  --set AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large `
  --non-interactive --json
```

Completa **senza** prompt e scrive `.sertor/.env`. Se manca un campo richiesto: **exit 1** con i nomi
dei mancanti, **nessuna** scrittura parziale.

---

## 3. Profilo locale (Ollama + Chroma) — nessun valore cloud

```powershell
sertor configure --backend local
```

Si completa **senza** chiedere alcun valore di servizio cloud (FR-006/SC-007); validazione `complete`,
exit `0`.

---

## 4. Riconfigurare senza distruggere

```powershell
# senza --overwrite: i valori già presenti sono preservati (o se ne chiede conferma con un TTY)
sertor configure --backend azure --set AZURE_OPENAI_ENDPOINT=https://nuovo.openai.azure.com/

# con --overwrite: sostituisce esplicitamente
sertor configure --backend azure --set AZURE_OPENAI_ENDPOINT=https://nuovo.openai.azure.com/ --overwrite
```

Righe e commenti non gestiti restano intatti. Ri-eseguire con gli stessi input → `.env` identico.

---

## 5. Verifica live opzionale (`--check`)

```powershell
sertor configure --backend azure --check
```

Dopo la validazione statica, tenta **una** chiamata di embedding reale verso il provider (via
`sertor-rag`) e ne riporta l'esito separatamente. Senza `--check` **non** viene fatta alcuna chiamata di
rete. Probe fallito → exit `1`, `.sertor/.env` **non** scartato.

---

## Cosa NON fa (confini)

- Non indicizza né crea l'indice (install≠run).
- Non configura le manopole opzionali (cache/observability/engine/graph): restano commentate nel
  template (estensione *Could*).
- Non offre provider/store non supportati dal core (solo Azure/Ollama, Chroma/Azure Search).
- Non scrive mai un segreto in un file versionato né a video/log.

---

## Exit code

`0` completa & valida · `1` incompleta/invalida o probe fallito · `2` uso errato (flag malformati).
