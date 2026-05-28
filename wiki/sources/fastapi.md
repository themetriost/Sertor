---
title: Fonte — fastapi/fastapi (corpus campione)
type: source
tags: [corpus, fastapi, code-rag, docs-rag]
created: 2026-05-28
updated: 2026-05-28
sources: [https://github.com/fastapi/fastapi]
---

# Fonte — `fastapi/fastapi` (corpus campione)

Repository pubblico scelto come **corpus campione** per il dual-RAG (vedi
[[architettura-target]]). Materializzato in `raw/fastapi/` come snapshot **immutabile**.

## Provenienza e fetch
- URL: https://github.com/fastapi/fastapi — licenza **MIT**, branch `master`.
- Fetch: clone **sparse + shallow** (`--depth 1 --filter=blob:none --sparse`) limitato a
  tre cartelle, così `raw/fastapi/` resta leggero (~34 MB, di cui ~13 MB `.git`).

## Contenuto rilevante
| Ruolo nel RAG | Cartella | Quantità |
|---------------|----------|----------|
| **Code RAG** | `raw/fastapi/fastapi/` | 48 file `.py` (il package) |
| **Docs RAG** | `raw/fastapi/docs/en/` | 153 file Markdown |
| **Link doc↔codice** | `raw/fastapi/docs_src/` | 454 esempi `.py` citati dai doc |

Le traduzioni (`docs/<lingua>/`) sono **escluse** dallo sparse-checkout.

## Perché questo corpus
- Codice Python pulito e di dimensioni gestibili in locale.
- Documentazione **ricca, separata e in Markdown** (loader semplici).
- `docs_src/` fornisce **relazioni doc↔codice esplicite** (una pagina di doc include uno
  specifico file di esempio): caso d'uso ideale per la fusione codice+documentazione.

## Note operative
- È una fonte in `raw/` → **sola lettura**, non modificare.
- Per aggiornare lo snapshot: `git -C raw/fastapi pull` (mantiene lo sparse-checkout).
