"""Le forme di un agente contro la sua sorgente (feature 006, research R5b).

Kaelen colloca lo stesso agente in forme diverse per assistente. Dopo una correzione della sorgente le
forme si rigenerano, e qui si verifica che nessuna abbia perso un limite che la sorgente ha. Una perdita che
la tabella di parità della 005 dichiara (per esempio `tools` su Codex) è `declared-loss`; ogni altra
differenza fa divergere la forma.

Un campo che un assistente rappresenta in modo diverso (`tools` e `model` su Copilot) non si può confrontare
per valore, perché il vocabolario è un altro. Se è presente nella forma esce come `unverified`, con i due
valori: non fa divergere la forma, ma resta visibile, perché `in-sync` non deve voler dire «coincide» su un
campo che nessuno ha confrontato (006, B3).
"""

from __future__ import annotations

from pathlib import Path

from . import config
from .agent_diff import prompt_lines, tool_items
from .domain.errors import InputError
from .domain.models import FormComparison, FormDifference, FormsReport
from .domain.ports import AgentSource


def compare_forms(source: Path, forms: list[Path], reader: AgentSource) -> FormsReport:
    src = reader.read(source)
    comparisons = []
    for form in forms:
        target = target_of(form)
        doc = reader.read(form)
        differences = _field_differences(src.header, doc.header, target)
        if prompt_lines(src) != prompt_lines(doc):
            differences.append(
                FormDifference("prompt", "prompt-differs", "il prompt non coincide con la sorgente")
            )
        comparisons.append(FormComparison(str(form), target, tuple(differences)))
    return FormsReport(str(source), config.PARITY_REFERENCE, tuple(comparisons))


def target_of(form: Path) -> str:
    name = form.name
    if name.endswith(".agent.md"):
        return "github-copilot"
    if name.endswith(".toml"):
        return "codex"
    if name.endswith(".md"):
        return "claude-code"
    raise InputError(str(form), "forma d'agente non riconosciuta (attese: .agent.md, .md, .toml)")


def _field_differences(source: dict, form: dict, target: str) -> list[FormDifference]:
    table = config.AGENT_PARITY[target]
    out = []
    for name in sorted(source):
        representation = table.get(name, config.PARITY_DEFAULT[target])
        if name not in form:
            kind = "missing" if representation == "represented" else "declared-loss"
            out.append(FormDifference(name, kind, f"'{name}' assente su {target}"))
        elif representation == "represented":
            if _value(name, source[name]) != _value(name, form[name]):
                out.append(FormDifference(name, "different", f"'{name}' diverso su {target}"))
        elif representation == "different":
            detail = (
                f"'{name}' non confrontabile su {target}: sorgente {source[name]!r}, forma {form[name]!r}"
            )
            out.append(FormDifference(name, "unverified", detail))
    return out


def _value(name: str, value):
    return frozenset(tool_items(value)) if name == "tools" else value
