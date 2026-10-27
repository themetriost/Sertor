"""Controlli meccanici su un file d'agente (feature 005, research R1–R6, R12): regole F, H, R, P, S, T.

Riporta l'intestazione come fatti (`tools` e `model` dichiarati o no) senza giudicarli: diventano difetti
solo nel giudizio della skill `agent-review`, quando il prompt o un brief ne dipende (R3). Le regole H e R
sono quelle del lint delle skill, applicate al prompt.
"""

from __future__ import annotations

from pathlib import Path

from . import config
from .adapters.agent_fs import FsAgentSource
from .domain.errors import InputError
from .domain.models import AgentDoc, AgentLintResult, Allowance, Finding
from .domain.ports import AgentSource
from .lint import _allowed, allowances_from, cited_paths, host_findings


def lint_agent(
    agent_file: Path,
    source: AgentSource | None = None,
    targets: list[str] | None = None,
    skills_dirs: list[Path] | None = None,
) -> AgentLintResult:
    targets = list(targets or [])
    unknown = [t for t in targets if t not in config.AGENT_TARGETS]
    if unknown:
        raise InputError("--targets", f"destinazione sconosciuta: {', '.join(unknown)}")
    missing_dirs = [str(d) for d in skills_dirs or [] if not Path(d).is_dir()]
    if missing_dirs:
        # una cartella sbagliata farebbe sembrare assenti tutte le skill nominate: è un errore d'ingresso
        raise InputError("--skills-dir", f"non è una cartella: {', '.join(missing_dirs)}")
    doc = (source or FsAgentSource()).read(agent_file)
    allowances = allowances_from(doc.header, doc.path)
    used: list[Allowance] = []
    named = _named_skills(doc, skills_dirs)
    parity = _parity(doc, targets)
    shells = _shell_tools(doc)
    h_severity = "blocking" if len(targets) >= 2 else "warning"
    findings = [
        *_header(doc),
        *host_findings(doc.body, allowances, used, _loc_of(doc), h_severity),
        *_bundled_references(doc),
        *_missing_skills(doc, named),
        *_parity_findings(parity),
        *_shell_findings(doc, shells, allowances, used),
        *_size(doc),
    ]
    return AgentLintResult(
        agent=doc.path,
        name=str(doc.header.get("name", "")),
        form=doc.form,
        facts={
            "fields": {k: v for k, v in doc.header.items() if k != "metadata"},
            "tools_declared": "tools" in doc.header,
            "model_declared": "model" in doc.header,
            "skills_named": named,
            "shell_tools": shells,
        },
        parity=parity,
        findings=tuple(findings),
        allowed=tuple(dict.fromkeys(used)),
    )


def _loc_of(doc: AgentDoc):
    def loc(line: int | None = None) -> str:
        return doc.file_name if line is None else f"{doc.file_name}:{line}"

    return loc


def _header(doc: AgentDoc) -> list[Finding]:
    loc = _loc_of(doc)()
    out = [
        Finding("F", "blocking", loc, f"intestazione senza il campo obbligatorio '{field}'")
        for field in ("name", "description")
        if not str(doc.header.get(field, "")).strip()
    ]
    name = str(doc.header.get("name", "")).strip()
    if name and name != doc.stem:
        out.append(Finding("F", "warning", loc, f"name '{name}' diverso dal nome del file '{doc.stem}'"))
    return out


def _bundled_references(doc: AgentDoc) -> list[Finding]:
    loc, base = _loc_of(doc), Path(doc.dir)
    out = []
    for n, line in doc.body:
        for path in cited_paths(line):
            if not (base / path.rstrip("/")).exists():
                out.append(Finding("R", "blocking", loc(n), f"allegato citato ma assente: {path}"))
    return out


def _named_skills(doc: AgentDoc, skills_dirs: list[Path] | None) -> list[dict]:
    names: dict[str, str] = {}  # nome → "backtick" se citato almeno una volta così, altrimenti "plain"
    for _, line in doc.body:
        for match, pattern in config.SKILL_NAME_PATTERNS:
            for name in pattern.findall(line):
                if names.get(name) != "backtick":
                    names[name] = match
    if not skills_dirs:
        return [{"name": n, "status": "unchecked", "match": m} for n, m in names.items()]
    return [
        {
            "name": n,
            "status": "found" if any((d / n / "SKILL.md").is_file() for d in skills_dirs) else "missing",
            "match": m,
        }
        for n, m in names.items()
    ]


def _missing_skills(doc: AgentDoc, named: list[dict]) -> list[Finding]:
    loc = _loc_of(doc)()
    out = []
    for s in named:
        if s["status"] != "missing":
            continue
        if s["match"] == "backtick":
            out.append(Finding("R", "blocking", loc, f"skill nominata ma assente: {s['name']}"))
        else:
            out.append(
                Finding("R", "warning", loc, f"possibile skill nominata (euristica), assente: {s['name']}")
            )
    return out


def _parity(doc: AgentDoc, targets: list[str]) -> dict:
    if not targets:
        return {"reference": config.PARITY_REFERENCE, "targets": [], "status": "not-applicable"}
    fields = [k for k in doc.header if k != "metadata"]
    entries = [
        {
            "target": t,
            "field": f,
            "representation": config.AGENT_PARITY[t].get(f, config.PARITY_DEFAULT[t]),
        }
        for t in targets
        for f in fields
    ]
    return {"reference": config.PARITY_REFERENCE, "targets": targets, "entries": entries}


def _parity_findings(parity: dict) -> list[Finding]:
    return [
        Finding(
            "P",
            "warning",
            f"{e['target']}:{e['field']}",
            f"campo '{e['field']}' {e['representation']} su {e['target']} ({parity['reference']})",
        )
        for e in parity.get("entries", [])
        if e["representation"] in ("dropped", "different")
    ]


def _tool_names(value) -> list[str]:
    items = value if isinstance(value, list) else str(value).strip().strip("[]").split(",")
    # `Bash(git *)` è lo strumento Bash con un filtro: conta come Bash
    return [str(i).strip().strip("'\"").split("(", 1)[0].strip() for i in items if str(i).strip()]


def _shell_tools(doc: AgentDoc) -> dict | None:
    """Le shell dichiarate e i sistemi su cui l'agente resta senza; None se la regola non si applica."""
    if doc.form != "markdown" or doc.file_name.endswith(".agent.md") or "tools" not in doc.header:
        return None  # Codex non riceve `tools`, Copilot ha un altro vocabolario, senza `tools` ha tutto
    declared = [t for t in dict.fromkeys(_tool_names(doc.header["tools"])) if t in config.SHELL_TOOLS]
    if not declared:
        return {"declared": [], "uncovered": []}  # se il prompt ne ha bisogno lo giudica la skill
    covered = {system for t in declared for system in config.SHELL_TOOLS[t]}
    return {"declared": declared, "uncovered": [s for s in config.OPERATING_SYSTEMS if s not in covered]}


def _shell_findings(doc: AgentDoc, shells: dict | None, allowances, used: list) -> list[Finding]:
    if not shells or not shells["uncovered"]:
        return []
    # un agente che non esegue comandi può tenere una sola shell: lo decide l'autore, dichiarandolo (006, B2)
    if _allowed("T", "claude-code:tools", allowances, used):
        return []
    missing = [t for t in config.SHELL_TOOLS if t not in shells["declared"]]
    return [
        Finding(
            "T",
            "blocking",
            "claude-code:tools",
            f"shell dichiarata solo per alcuni sistemi ({', '.join(shells['declared'])}): su "
            f"{', '.join(shells['uncovered'])} l'agente resta senza shell; "
            f"se il prompt esegue comandi, aggiungi {', '.join(missing)}",
        )
    ]


def _size(doc: AgentDoc) -> list[Finding]:
    if len(doc.body) <= config.MAX_BODY_LINES:
        return []
    return [
        Finding(
            "S",
            "warning",
            _loc_of(doc)(),
            f"prompt di {len(doc.body)} righe, oltre {config.MAX_BODY_LINES}: "
            "rimanda a una skill o a un allegato",
        )
    ]
