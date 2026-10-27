# Le regole che una skill scritta con questa skill deve rispettare, e perché

Sono le lezioni che Sinthari ha imparato scrivendo e rivedendo skill, proprie e di altri nodi. La revisione
le applica dopo; questa skill le applica mentre scrive. Per ogni regola è indicato chi la difende:
**costruzione** vuol dire che la garantisce un runtime, uno schema o un gate, e l'agente non può violarla
nemmeno volendo; **promessa** vuol dire che la tiene il giudizio dell'agente, e può cedere sotto pressione.

| # | Regola | Perché | Difesa |
|---|---|---|---|
| 1 | Nel corpo nessun percorso di un assistente (`.claude/…`, `.github/…`) e nessuna invocazione slash | Lo stesso corpo deve funzionare su ogni assistente; un percorso che esiste su un ospite su un altro non porta da nessuna parte | costruzione (`lint` H) |
| 2 | Ogni file citato dal corpo viaggia con la skill | Un agente che riceve solo la skill non può aprire un file rimasto nel repo di sviluppo: si ferma o indovina | costruzione (`lint` R) |
| 3 | Ogni regola lasciata al giudizio porta il suo perché | Un agente capace tiene la linea meglio quando sa il motivo; un MUST nudo cede al primo buon argomento | promessa (la controlla la revisione) |
| 4 | Per ogni regola di giudizio, chiedersi: la può garantire un runtime, uno schema o un controllo meccanico? | Il rischio residuo di una skill vive quasi tutto nelle promesse; spostarne una nel runtime la trasforma in garanzia | promessa, con la risposta registrata |
| 5 | Ogni garanzia deterministica dichiara il suo confine | Un comando che nasconde contenuto protegge il canale agente↔utente, non i dati a riposo; dirlo evita un falso senso di sicurezza | promessa (la controlla la revisione) |
| 6 | Corpo snello; il materiale lungo va negli allegati, citati per nome | Il corpo l'agente lo legge ogni volta, un allegato solo quando serve | costruzione per la lunghezza (`lint` S), promessa per il resto |
| 7 | Un esempio lavorato e una sezione sui modi di guasto | Senza esempio l'agente deduce la forma attesa; senza modi di guasto improvvisa quando qualcosa si rompe | costruzione per la presenza (`lint` M), promessa per la qualità |
| 8 | Una regola dura non contraddice mai un passo operativo della stessa skill | Un agente che segue "fallisci in modo visibile" si blocca quando una regola vieta ciò che un passo richiede | promessa (la controlla la revisione) |
| 9 | Una skill si giustifica per ciò che **garantisce**, non per ciò che suggerisce | Un agente capace senza la skill il suggerimento lo trova da solo: nel collaudo di Vestiger ha retto su 3 casi su 4 | misurata (`verdict`) |
| 10 | I casi di prova separano la skill dal baseline **sul merito** | Le asserzioni misurano ciò che sai già di voler misurare: 5 su 6 misuravano il protocollo, non il risultato | costruzione (`verdict`, `ready`) |
| 11 | Chi ha scritto non è chi valuta | Chi ha scritto un testo ci ritrova la propria intenzione invece della riga; un secondo lettore trova ciò che l'autore non vede | promessa, dichiarata come confine |
| 12 | Una skill si dichiara pronta solo attraverso il gate | Sotto pressione ("va bene così, chiudi") il bloccante è la prima cosa che si salta | costruzione (`ready`) |

## Da dove vengono

- **`skill-review`:** la lente costruzione/promessa, il test del freddo, la checklist delle dimensioni.
- **Il collaudo delle skill di Vestiger (2026-08-06):** merito contro protocollo, il baseline che non è un
  uomo di paglia, il secondo lettore.
- **Il modo di consegnare di Sinthari:** skill sottile più runtime deterministico, con il runtime che fa ciò
  che non deve dipendere dal giudizio.
