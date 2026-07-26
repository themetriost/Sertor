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
from pathlib import Path


def node_root():
    """La radice del nodo, dedotta **dalla posizione di questo file** (`<nodo>/.claude/hooks/…`).

    Non da una variabile d'ambiente dell'ospite: l'hook deve restare host-agnostico e funzionare
    qualunque sia la cwd da cui l'assistente lo lancia.
    """
    return Path(__file__).resolve().parents[2]


def occasion_command():
    """L'invocazione **node-scoped** (FR-RUN-06): dalla v0.5.0 la capability vive nel nodo, non nella
    macchina, e il comando nudo `acta` non esiste più come contratto.

    Duplica di proposito la forma definita in `acta.node_runtime.node_command`: questo hook gira con un
    interprete nudo (`uv run --no-project python`) e **non può importare `acta`** — se potesse, dovrebbe
    già essere dentro il runtime che sta cercando di raggiungere. Un test di parità tiene allineate le
    due copie.
    """
    return [
        "uv", "run", "--project", str(node_root() / ".acta"), "acta", "occasion", "--json",
    ]


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
    if esito == "runtime-non-disponibile":
        # FR-RUN-10: il runtime del nodo può mancare (non installato, non materializzato, `uv` assente).
        # Si DICHIARA — mai si sopprime — ma non si blocca la sessione.
        return (
            "OCCASIONE ACTA — runtime del nodo non disponibile: la bacheca non è stata guardata. "
            f"({outcome.get('dettaglio', '')}) "
            "Rimedio: dalla radice del nodo esegui `acta install` (bootstrap: "
            "`uvx --from git+https://github.com/themetriost/Acta acta install`)."
        )
    # silenzio / prima-visita / esito ignoto → nessuna direttiva (nessun falso avviso, SC-005)
    return None


def _run_occasion():
    """Esegue l'occasione **nel runtime del nodo** e ne restituisce l'esito come dict.

    Fail-soft ma **fail-loud** (Cost. XI): un runtime assente o rotto non deve rompere la sessione, ma
    non deve nemmeno passare per «nessuna novità» — sarebbe un silenzio che mente. Perciò si distingue
    *non c'è niente di nuovo* (None) da *non ho potuto guardare* (esito dichiarato, FR-RUN-10).
    """
    try:
        result = subprocess.run(occasion_command(), capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return {"esito": "runtime-non-disponibile", "dettaglio": "`uv` non trovato su questo host"}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"esito": "runtime-non-disponibile", "dettaglio": f"{type(exc).__name__}"}
    out = (result.stdout or "").strip()
    if not out:
        if result.returncode != 0:
            detail = (result.stderr or "").strip().splitlines()
            return {
                "esito": "runtime-non-disponibile",
                "dettaglio": detail[-1][:200] if detail else f"exit {result.returncode}",
            }
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
