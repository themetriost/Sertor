# Quickstart — provare lo smoke di upgrade

**Feature**: `125-smoke-di-upgrade` · **Date**: 2026-07-29

Tutti i comandi in PowerShell, dalla radice del repo.

## Il percorso automatico (quello che gira al rilascio)

```powershell
.\scripts\smoke.ps1 -FromRef (git describe --tags --abbrev=0) -Ref master -Assistant claude -Capability rag
```

Installa la release precedente su un host usa-e-getta, aggiorna a `master`, e asserisce i cinque esiti.

## Il percorso completo (a richiesta)

Tutte le combinazioni più il salto lungo. In CI si avvia a mano dall'interfaccia delle Actions; in
locale si lancia una combinazione per volta cambiando `-Assistant` e `-Capability`.

```powershell
foreach ($a in @("claude","copilot-cli")) {
  foreach ($c in @("rag","wiki")) {
    .\scripts\smoke.ps1 -FromRef (git describe --tags --abbrev=0) -Ref master -Assistant $a -Capability $c
  }
}
```

## Il salto lungo

```powershell
.\scripts\smoke.ps1 -FromRef v0.3.0 -Ref master -Assistant claude -Capability rag
```

È la condizione in cui il difetto del pin è emerso davvero: un ospite fermo a `v0.3.0` che aggiorna in
un passo.

## Che il comportamento esistente non sia cambiato

Senza `-FromRef` lo script deve fare **esattamente** ciò che faceva:

```powershell
.\scripts\smoke.ps1 -Ref master -Assistant claude -Capability rag
```

## Leggere l'esito

- **successo** → l'aggiornamento è avvenuto e i cinque esiti reggono.
- **divergenza di prodotto** → il messaggio **nomina** quale esito non regge e su quale
  assistente/piattaforma. Non serve rieseguire per capire.
- **impedimento d'ambiente** → manca un prerequisito (rete, `uvx`, ref non raggiungibile). **Non** è un
  difetto di prodotto e va letto come tale.

## La verifica che conta davvero, la prima volta

Dopo l'implementazione, lanciarlo sui **tre riscontri del nodo *Acta*** del 2026-07-29 — gate del wiki,
`wiki-curator`, falso positivo del `lint` — per stabilire se un ospite che **aggiorna** li riceve
davvero. È la condizione posta per il rilascio, ed è anche il primo test reale di SC-001.
