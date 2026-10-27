# Parità di un agente fra assistenti

Fonte di riferimento: le regole di collocazione del motore d'installazione della federazione (Kaelen
0.16.1). Il runtime la dichiara nell'esito (`parity.reference`). Se la fonte cambia versione, questa
tabella va riverificata.

## Come ogni assistente riceve lo stesso agente

| assistente | forma | cosa porta |
|---|---|---|
| Claude Code | file Markdown con intestazione, copiato com'è | tutta l'intestazione e il prompt |
| GitHub Copilot | file `.agent.md`, copiato com'è | tutta l'intestazione e il prompt, ma i valori di `tools` e `model` sono letti col vocabolario di Copilot |
| Codex | file TOML scritto dal motore | solo `name`, `description` e il prompt (`developer_instructions`): ogni altro campo si perde |

## Cosa vuol dire ogni esito

| esito | significato | cosa controllare |
|---|---|---|
| `represented` | il campo arriva e ha lo stesso significato | niente |
| `different` | il campo arriva, ma con un altro vocabolario: `Read, Bash` o `haiku` sono nomi di Claude Code, e non è garantito che Copilot li riconosca | il limite che il campo esprime regge anche se il campo viene ignorato? |
| `dropped` | il campo non arriva | il limite è ripetuto nel prompt? Se no, su quell'assistente l'agente non ha quel limite |
| `unknown` | la fonte non dice come l'assistente tratta il campo | segnalalo come incertezza, non come difetto |

## Limiti dichiarati

- La colonna Copilot (`different`) viene dalle regole di collocazione (file copiato com'è) e dal fatto che
  i nomi degli strumenti differiscono fra assistenti. Non è stata provata su un Copilot reale: dillo nel
  rapporto quando un finding ne dipende.
- Un limite scritto **nel prompt** viaggia su tutti gli assistenti, ma è una promessa (lo tiene il
  giudizio dell'agente). Un limite scritto **nell'intestazione** è una costruzione, ma solo dove il campo
  arriva. La correzione tipica di un `dropped` su un confine importante è averlo in entrambi i posti.

## Anche il sistema operativo è un asse

La parità non è solo fra assistenti: sullo stesso assistente un agente può girare su Linux, macOS o
Windows, e alcuni strumenti esistono solo su alcuni sistemi (la shell di Claude Code si chiama `Bash` o
`PowerShell`). Questo asse vale anche per un agente di un solo assistente, e si giudica nella dimensione 1
(«gli strumenti bastano?») di `references/dimensions.md`, non qui.

## Quando non si applica

Se l'agente è destinato a un solo assistente (per esempio vive solo nella cartella degli agenti di Claude
Code e nessuna dichiarazione d'installazione lo porta altrove), la parità non si applica: chiama il runtime
senza `--targets` e scrivi "parità non applicabile" nel rapporto.
