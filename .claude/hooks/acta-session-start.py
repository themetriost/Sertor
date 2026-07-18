"""SessionStart — l'**occasione della scoperta** di Acta (FR-DIS-13/14).

Invoca `acta occasion --json` (che aggiorna la bacheca e rileva le novità dall'ultima visita) e ne
emette l'ANNUNCIO — i **soli metadati**, mai i corpi (FR-DIS-14) — come contesto di inizio sessione:
come gli altri hook di SessionStart, *annuncia* invece di iniettare. È il nodo che decide di guardare,
non la bacheca che bussa.

Autonomo e **stdlib-only** (nessuna dipendenza da `_hooklib` o dalla struttura dell'host — la lezione di
Noetix: «non assumere la forma dell'ospite»). Portabile: `--assistant claude|copilot`.

**Fail-soft ma fail-loud (Cost. XI):** esce SEMPRE 0 (non blocca mai la sessione né i tool: è
SessionStart, non PreToolUse), ma se l'occasione riporta un guasto d'accesso lo **dichiara** invece di
sopprimerlo. Non persiste alcun verdetto: misura al momento (nessun rischio del difetto `rag-freshness`,
dove un verdetto vecchio veniva ripubblicato).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def build_directive(outcome):
    """Dall'esito JSON dell'occasione alla direttiva di SessionStart, o **None** (= silenzio: nessun
    contesto emesso). Funzione **pura** (nessun I/O) → testabile in isolamento."""
    if not isinstance(outcome, dict):
        return None
    esito = outcome.get("esito")
    if esito == "accesso-non-riuscito":
        return (
            "OCCASIONE ACTA — accesso non riuscito: la bacheca non è stata aggiornata "
            f"({outcome.get('dettaglio', '')}). Nessuna novità è garantita finché non si risolve; "
            "puoi riprovare con `acta occasion`."
        )
    if esito == "novita":
        novita = outcome.get("novita") or []
        if not novita:
            return None
        dove = "nei canali che segui" if outcome.get("canali") else "sulla bacheca Acta"
        lines = [
            f"OCCASIONE ACTA — {len(novita)} novità {dove}. Sono METADATI, non i contenuti: "
            "per leggere un corpo decidi tu e lancia `acta discover`."
        ]
        for n in novita:
            tags = n.get("tags") or []
            tag_str = (" [" + ", ".join(tags) + "]") if tags else ""
            lines.append(
                f"- [{n.get('canale')}] {n.get('titolo')} — nodo {n.get('nodo')}, {n.get('data')}{tag_str}"
            )
        return "\n".join(lines)
    # silenzio / prima-visita / esito ignoto → nessuna direttiva (nessun falso avviso, SC-005)
    return None


def _run_occasion():
    """Esegue `acta occasion --json` e ne restituisce l'esito come dict, o **None** se non disponibile.
    Fail-soft: `acta` assente o in errore non deve rompere la sessione."""
    try:
        result = subprocess.run(
            ["acta", "occasion", "--json"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = (result.stdout or "").strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assistant", default="claude")
    args, _ = parser.parse_known_args()
    # stdin-guard: non bloccare in attesa dell'evento (se non è una pipe interattiva, prosegui).
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass

    directive = build_directive(_run_occasion())
    if not directive:
        return
    if args.assistant == "copilot":
        print(json.dumps({"additionalContext": directive}))  # VS Code additionalContext
    else:
        print(directive)  # claude: stdout = contesto SessionStart


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-safe: l'occasione non rompe MAI la sessione (Cost. XI)
    sys.exit(0)
