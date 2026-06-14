---
title: Metterlo su un progetto (in parole semplici)
type: explainer
tags: [non-tecnici, installer, portabilità, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/tech/sertor-installer.md", "docs/install.md"]
---

# Metterlo su un progetto

## Il problema

Uno strumento è utile solo se è **facile da mettere in casa**. Se per usare Sertor su un nuovo
progetto servissero ore di configurazione manuale, nessuno lo userebbe. E non deve **sporcare** il
progetto ospite: niente file sparsi, niente cose sovrascritte di nascosto.

## L'idea

Sertor si installa su un progetto **con un comando**. L'installazione prepara il necessario (le
impostazioni, il collegamento all'assistente) in modo **ordinato e prevedibile**, tenendo i propri
file in un angolo dedicato e senza toccare il lavoro che c'è già.

Due principi che ci teniamo a rispettare:

- **Installare ≠ partire.** Installare prepara soltanto; il lavoro pesante (leggere e schedare il
  progetto) parte solo quando lo chiedi tu. Nessuna sorpresa costosa al momento dell'installazione.
- **Non distruttivo.** Se hai già dei tuoi file, Sertor non li sovrascrive: si affianca.
- **Si rifà senza danni.** Se lanci l'installazione due volte, non combina pasticci: riconosce cosa
  c'è già.

## Perché conta

Sertor è pensato per stare su **qualunque** progetto — fatto di solo codice, solo documenti, o
entrambi — senza essere riscritto per l'occasione: ciò che cambia da progetto a progetto sta nelle
*impostazioni*, non nello strumento. È la differenza tra un elettrodomestico universale e uno costruito
su misura per una sola cucina.

## L'immagine

È un elettrodomestico che monti in qualsiasi cucina: lo appoggi, lo colleghi, e funziona — senza dover
rifare l'impianto e senza buttare via i mobili che hai già.

---

*Dettaglio tecnico:* l'installer è descritto in [[sertor-installer]]; la guida operativa in
`docs/install.md`. Il principio di portabilità è il [[constitution|Principio X]].
