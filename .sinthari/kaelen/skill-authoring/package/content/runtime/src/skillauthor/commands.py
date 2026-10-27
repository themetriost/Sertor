"""Collegamento dei sottocomandi al CLI (composition root): adapter concreti scelti solo qui.

Ogni `register_*` aggiunge un sottocomando con il suo handler. L'handler restituisce il codice d'uscita
(0 esito positivo, 1 esito negativo di dominio); gli errori d'ingresso salgono come eccezioni e il CLI li
traduce in 2.
"""

from __future__ import annotations

from pathlib import Path

from .adapters.agent_fs import FsAgentSource
from .agent_diff import diff_agents
from .agent_forms import compare_forms
from .agent_lint import lint_agent
from .cost import compute_cost
from .digest import agent_digest, skill_digest
from .domain.errors import InputError
from .lint import lint_skill
from .observability import log_command
from .parity import compare
from .ready import evaluate_ready
from .verdict import compute_verdict

EXIT_OK, EXIT_NEGATIVE = 0, 1


def _emit(document: dict, as_json: bool, text: str) -> None:
    from .cli import emit

    emit(document, as_json, text)


# --- lint --------------------------------------------------------------------------------


def _lint(args) -> int:
    result = lint_skill(Path(args.skill_dir))
    lines = [f"{f.severity:8} {f.rule} {f.location}  {f.detail}" for f in result.findings]
    lines += [f"allowed  {a.rule} '{a.match}'  ({a.why})" for a in result.allowed]
    summary = "bloccanti presenti" if result.has_blocking else "nessun bloccante"
    _emit(
        result.to_dict(), args.json, "\n".join([*lines, f"lint: {summary} ({len(result.findings)} finding)"])
    )
    log_command("lint", f"{args.skill_dir}: {len(result.findings)} finding")
    return EXIT_NEGATIVE if result.has_blocking else EXIT_OK


def register_lint(sub) -> None:
    p = sub.add_parser("lint", help="controlli deterministici di forma su una skill (H R F S M L)")
    p.add_argument("skill_dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_lint)


# --- cost --------------------------------------------------------------------------------


def _cost(args) -> int:
    evals_file = Path(args.evals) if args.evals else None
    cost = compute_cost(Path(args.skill_dir), runs=args.runs, evals_file=evals_file)
    text = (
        f"collaudo: {cost.cases} casi × 2 configurazioni × {cost.runs} giri = {cost.executions} esecuzioni "
        f"+ {cost.gradings} valutazioni"
    )
    _emit(cost.to_dict(), args.json, "\n".join([text, *(f"avviso: {w}" for w in cost.warnings)]))
    return EXIT_OK


def register_cost(sub) -> None:
    p = sub.add_parser("cost", help="costo del collaudo dichiarato prima di lanciarlo")
    p.add_argument("skill_dir")
    p.add_argument("--evals", help="file dei casi (default: <skill-dir>/evals/evals.json)")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_cost)


# --- verdict -----------------------------------------------------------------------------


def _verdict(args) -> int:
    evals = Path(args.evals)
    skill = (
        Path(args.skill) if args.skill else (evals.parent.parent if evals.parent.name == "evals" else None)
    )
    verdict = compute_verdict(Path(args.workspace), evals, skill_dir=skill)
    lines = [
        f"{'separa' if o.separates else '      '} {o.kind:8} eval-{o.eval_id} "
        f"{o.pass_rate_with:.2f} vs {o.pass_rate_without:.2f}  {o.text}"
        for o in verdict.per_expectation
    ]
    lines += [f"mancante: {m}" for m in verdict.missing]
    lines += [
        f"contestato: eval-{c['eval_id']} '{c['text']}' → {c['proposed_kind']} ({c['why']})"
        for c in verdict.kind_challenges
    ]
    _emit(verdict.to_dict(), args.json, "\n".join([*lines, f"verdetto: {verdict.verdict}"]))
    return EXIT_OK


def register_verdict(sub) -> None:
    p = sub.add_parser("verdict", help="verdetto di separazione merito/protocollo dalle valutazioni")
    p.add_argument("workspace")
    p.add_argument("--evals", required=True)
    p.add_argument(
        "--skill",
        help="skill (cartella) o agente (file) collaudato (default: la cartella che contiene evals/)",
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_verdict)


# --- ready -------------------------------------------------------------------------------


def _ready(args) -> int:
    result = evaluate_ready(
        Path(args.skill_dir),
        Path(args.review),
        Path(args.verdict),
        accept_unvalidated=args.accept_unvalidated,
        previous_review=Path(args.previous_review) if args.previous_review else None,
        forms=[Path(f) for f in args.form or []],
    )
    lines = [f"motivo: {r.code}  {r.detail}" for r in result.reasons]
    lines += [f"accettato: {a['what']}  ({a['reason']})" for a in result.accepted]
    _emit(result.to_dict(), args.json, "\n".join([*lines, f"stato: {result.status}"]))
    return EXIT_NEGATIVE if result.status == "not-ready" else EXIT_OK


def register_ready(sub) -> None:
    p = sub.add_parser("ready", help="gate: l'unico modo di dichiarare pronta una skill o un agente")
    p.add_argument("skill_dir", metavar="skill-dir|agent-file")
    p.add_argument("--review", required=True)
    p.add_argument("--verdict", required=True)
    p.add_argument(
        "--previous-review", help="registro del giro precedente, per rilevare i bloccanti ricomparsi"
    )
    p.add_argument("--accept-unvalidated", metavar="MOTIVO")
    p.add_argument("--form", action="append", help="forma derivata di un agente da verificare, ripetibile")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_ready)


# --- parity ------------------------------------------------------------------------------


def _parity(args) -> int:
    result = compare(Path(args.a), Path(args.b))
    if result.identical:
        text = "parity: identiche"
    else:
        diff = result.first_difference
        text = f"parity: diverse, prima differenza {diff['kind']} su {diff['path']}"
    _emit(result.to_dict(), args.json, text)
    return EXIT_OK if result.identical else EXIT_NEGATIVE


def register_parity(sub) -> None:
    p = sub.add_parser("parity", help="confronto byte per byte di due cartelle o due file")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_parity)


# --- digest ------------------------------------------------------------------------------


def _digest(args) -> int:
    target = Path(args.skill_dir)
    if target.is_file():
        digest = agent_digest(target)
        _emit({"agent_file": str(target), "agent_digest": digest}, args.json, f"digest: {digest}")
        return EXIT_OK
    if not target.is_dir():
        raise InputError("skill_dir", f"non esiste: {target}")
    digest = skill_digest(target)
    _emit({"skill_name": target.resolve().name, "skill_digest": digest}, args.json, f"digest: {digest}")
    return EXIT_OK


def register_digest(sub) -> None:
    p = sub.add_parser(
        "digest", help="impronta di una cartella-skill o di un file d'agente, la stessa che verdict registra"
    )
    p.add_argument("skill_dir", metavar="skill-dir|agent-file")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_digest)


# --- agent-lint --------------------------------------------------------------------------


def _agent_lint(args) -> int:
    targets = [t.strip() for t in args.targets.split(",") if t.strip()] if args.targets else []
    result = lint_agent(
        Path(args.agent_file), targets=targets, skills_dirs=[Path(d) for d in args.skills_dir or []]
    )
    facts = result.facts
    lines = [
        f"fatto    tools: {facts['fields'].get('tools', '(non dichiarato)')}",
        f"fatto    model: {facts['fields'].get('model', '(non dichiarato)')}",
        *(f"skill    {s['name']}  {s['status']}" for s in facts["skills_named"]),
        *(f"{f.severity:8} {f.rule} {f.location}  {f.detail}" for f in result.findings),
        *(f"allowed  {a.rule} '{a.match}'  ({a.why})" for a in result.allowed),
    ]
    if result.parity.get("status") == "not-applicable":
        lines.append("parità   non applicabile (nessuna destinazione)")
    summary = "bloccanti presenti" if result.has_blocking else "nessun bloccante"
    _emit(
        result.to_dict(),
        args.json,
        "\n".join([*lines, f"agent-lint: {summary} ({len(result.findings)} finding)"]),
    )
    log_command("agent-lint", f"{args.agent_file}: {len(result.findings)} finding")
    return EXIT_NEGATIVE if result.has_blocking else EXIT_OK


def register_agent_lint(sub) -> None:
    p = sub.add_parser("agent-lint", help="controlli deterministici su un file d'agente (F H R P S T)")
    p.add_argument("agent_file")
    p.add_argument("--targets", help="destinazioni separate da virgola: claude-code,github-copilot,codex")
    p.add_argument(
        "--skills-dir", action="append", help="cartella di skill (<dir>/<nome>/SKILL.md), ripetibile"
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_agent_lint)


# --- agent-diff --------------------------------------------------------------------------


def _agent_diff(args) -> int:
    result = diff_agents(Path(args.before), Path(args.after), FsAgentSource())
    lines = [f"{c.change:8} {c.field}: {c.before} → {c.after}" for c in result.fields]
    if result.tools is not None:
        added = " ".join(f"+{t}" for t in result.tools["added"])
        removed = " ".join(f"−{t}" for t in result.tools["removed"])
        lines.append(f"tools    {' '.join(x for x in (added, removed) if x) or 'invariati'}")
    prompt = result.prompt
    lines.append(
        f"prompt   cambiato: +{prompt['lines_added']} −{prompt['lines_removed']} righe"
        if prompt["changed"]
        else "prompt   invariato"
    )
    _emit(result.to_dict(), args.json, "\n".join(lines))
    log_command("agent-diff", f"{args.before} → {args.after}: {len(result.fields)} campi")
    return EXIT_OK


def register_agent_diff(sub) -> None:
    p = sub.add_parser(
        "agent-diff", help="differenze d'intestazione e di prompt fra due versioni di un agente"
    )
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_agent_diff)


# --- agent-forms -------------------------------------------------------------------------


def _agent_forms(args) -> int:
    report = compare_forms(Path(args.source), [Path(f) for f in args.forms], FsAgentSource())
    lines = [
        f"{f.status:22} {f.file} ({f.target})"
        + (": " + ", ".join(f"{d.field} {d.kind}" for d in f.differences) if f.differences else "")
        for f in report.forms
    ]
    diverging = sum(f.status == "diverges" for f in report.forms)
    lines.append(f"agent-forms: {diverging} forme divergono ({report.reference})")
    _emit(report.to_dict(), args.json, "\n".join(lines))
    log_command("agent-forms", f"{args.source}: {diverging} forme divergono")
    return EXIT_OK if report.in_sync else EXIT_NEGATIVE


def register_agent_forms(sub) -> None:
    p = sub.add_parser("agent-forms", help="confronta le forme di un agente con la sua sorgente")
    p.add_argument("source")
    p.add_argument("forms", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_agent_forms)


REGISTRY = [
    register_lint,
    register_cost,
    register_verdict,
    register_ready,
    register_parity,
    register_digest,
    register_agent_lint,
    register_agent_diff,
    register_agent_forms,
]
