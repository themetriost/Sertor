## Skill authoring di Sinthari

In questo repository è installata la capability **skill-authoring** del nodo Sinthari: serve a scrivere,
modificare, collaudare e rivedere skill.

- **Per creare o modificare una skill** usa la skill `skill-authoring`. Accompagna il lavoro in sei passi
  (intento, scrittura, confine fra skill e runtime, collaudo, revisione, chiusura) e la dichiara pronta solo
  con il gate del runtime.
- **Per un parere su una skill senza modificarla** usa la skill `skill-review`.
- **Per un parere sulla definizione di un agente** (intestazione e prompt) senza modificarla usa la skill
  `agent-review`.
- **Per delegare la scrittura di una skill** usa l'agente `skill-author`, dove l'assistente supporta gli
  agenti. Altrove basta la skill.
- **Per correggere la definizione di un agente** a partire dalla sua review usa la skill `agent-authoring`:
  propone una modifica per finding, fa approvare a parte i cambi d'intestazione, collauda l'agente corretto contro
  quello di prima e lo dichiara pronto solo con il gate del runtime.
- **Per delegare la correzione di un agente** usa l'agente `agent-author`, dove l'assistente supporta gli agenti.
  Altrove basta la skill.

**Il runtime `skillauthor`.** I controlli che non richiedono giudizio (lint di skill e di agenti, differenze e
forme di un agente, costo del collaudo, impronta, verdetto, gate, parità) li fa un programma, installato in un ambiente proprio della capability. Si invoca
dalla radice del repository, con Python 3.12 o successivo:

```
python .sinthari/kaelen/skill-authoring/launch.py skillauthor <comando> …
```

Dove la skill scrive `skillauthor <comando>`, usa questa forma. `--help` elenca i comandi. Se il launcher
risponde che l'ambiente non è costruito, va ripetuta l'installazione della capability su questa macchina:
non sostituire il runtime con un controllo a occhio.
