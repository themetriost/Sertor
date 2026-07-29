# Contract — la superficie dello smoke di upgrade

**Feature**: `125-smoke-di-upgrade` · **Date**: 2026-07-29

## Superficie dello script

`scripts/smoke.ps1` / `scripts/smoke.sh` — **un parametro nuovo**, il resto invariato.

| Parametro | Esistente? | Significato |
|---|---|---|
| `-Ref` | sì | ref a cui si arriva (default `master`) |
| `-Assistant` | sì | `claude` \| `copilot-cli` |
| `-Capability` | sì | `rag` \| `wiki` \| `flow` |
| `-Target` | sì | repo già clonato (solo `rag`) |
| **`-FromRef`** | **nuovo** | ref **da cui si parte**. Assente → comportamento odierno (solo install). Valorizzato → install da `FromRef`, poi **upgrade** a `Ref`, poi asserzioni d'esito |

**Compatibilità**: senza `-FromRef` lo script si comporta **esattamente** come oggi. Nessuna
invocazione esistente cambia.

## Gli esiti asseriti dopo l'aggiornamento

Elenco **in un solo punto** dello script (FR-015): aggiungerne uno dopo un difetto nuovo è una riga in
più, non una ristrutturazione.

| # | Esito | Difetto reale che lo giustifica |
|---|---|---|
| 1 | il **pin** punta alla versione in uscita | pin fermo dopo l'upgrade (3 nodi indipendenti) |
| 2 | l'automatismo di sessione è **uno solo** e aggiornato | hook duplicati al ri-cablaggio (E10-FEAT-032) |
| 3 | la **configurazione dell'ospite** è preservata | il fix di E2-FEAT-022 rischiò di azzerare il corpus |
| 4 | la **forma dell'invocazione** registrata è quella corrente | `--directory` conservato perché «c'era già» |
| 5 | la **salute** è verde | verifica d'insieme |

## Gli esiti di uscita

| Esito | Significato | Chi lo causa |
|---|---|---|
| **successo** | l'aggiornamento è avvenuto e tutti gli esiti asseriti reggono | — |
| **divergenza di prodotto** | almeno un esito asserito **non** regge; il messaggio **nomina** l'esito e il contesto (assistente, piattaforma) | un difetto |
| **impedimento d'ambiente** | un prerequisito manca (rete, `uvx`, ref non raggiungibile) | l'ambiente, **non** il prodotto |

**Perché tre e non due**: un rosso indistinto insegna a ignorare il gate. È la stessa dinamica per cui
è esistita la v0.3.3 — *una guardia che segnala il falso insegna a smettere di leggerla*.

## I due percorsi d'esecuzione

| Percorso | Quando | Perimetro | Vincolante? |
|---|---|---|---|
| **automatico** | a ogni rilascio | **una** combinazione, dall'ultima release | **sì** |
| **completo** | **a richiesta** | tutte le combinazioni + un **salto lungo** | no |

L'esclusione del percorso completo da quello automatico **va dichiarata dove la si documenta**
(FR-013): una copertura che nessuno sa di dover lanciare è copertura solo sulla carta.
