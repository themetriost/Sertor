"""Lint deterministico di una skill (research R6): regole H, R, F, S, M, L.

Controlla la forma, non il merito: che il corpo non dipenda da un assistente, che gli allegati citati
esistano, che il frontmatter regga, che il corpo resti snello e maturo, che il materiale vendorizzato
porti licenza e avviso. Il perché delle regole di giudizio resta alla revisione.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import config
from .adapters.skill_fs import FsSkillSource
from .domain.errors import InputError
from .domain.models import Allowance, Finding, LintResult, SkillDoc
from .domain.ports import SkillSource

_MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
_BACKTICK = re.compile(r"`([^`\s]+)`")


def lint_skill(skill_dir: Path, source: SkillSource | None = None) -> LintResult:
    doc = (source or FsSkillSource()).read(skill_dir)
    allowances = allowances_from(doc.frontmatter, str(skill_dir / "SKILL.md"))
    used: list[Allowance] = []
    findings = [
        *host_findings(doc.body, allowances, used, _loc, "blocking"),
        *_bundled_references(doc),
        *_frontmatter(doc),
        *_size(doc),
        *_maturity(doc),
        *_licenses(doc),
    ]
    return LintResult(skill_dir=str(skill_dir), findings=tuple(findings), allowed=tuple(dict.fromkeys(used)))


def _loc(line: int | None = None) -> str:
    return "SKILL.md" if line is None else f"SKILL.md:{line}"


def allowances_from(frontmatter: dict, path: str) -> tuple[Allowance, ...]:
    """Le eccezioni dichiarate in `metadata.lint-allow` (condivise con agent-lint)."""

    raw = (
        frontmatter.get("metadata", {}).get("lint-allow", [])
        if isinstance(frontmatter.get("metadata"), dict)
        else []
    )
    out = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or not all(
            str(entry.get(k, "")).strip() for k in ("rule", "match", "why")
        ):
            raise InputError(path, f"metadata.lint-allow[{i}] richiede rule, match e why non vuoti")
        out.append(Allowance(str(entry["rule"]), str(entry["match"]), str(entry["why"])))
    return tuple(out)


def _allowed(rule: str, line: str, allowances: tuple[Allowance, ...], used: list[Allowance]) -> bool:
    for a in allowances:
        if a.rule == rule and a.match in line:
            used.append(a)
            return True
    return False


def host_findings(body, allowances, used, loc, severity) -> list[Finding]:
    """Regola H su un corpo numerato: percorsi e invocazioni propri di un assistente."""

    out = []
    for n, line in body:
        for pattern in config.HOST_PATH_PATTERNS:
            m = pattern.search(line)
            if m and not _allowed("H", line, allowances, used):
                out.append(
                    Finding("H", severity, loc(n), f"percorso di un assistente nel corpo: {m.group(0)}")
                )
        m = config.SLASH_PATTERN.search(line)
        if m and not _allowed("H", line, allowances, used):
            out.append(
                Finding("H", severity, loc(n), f"invocazione slash nel corpo: {m.group(0).strip(' `')}")
            )
    return out


def cited_paths(line: str) -> list[str]:
    """Percorsi di allegati citati in una riga (link Markdown o backtick), condivisi con agent-lint."""

    candidates = [*_MD_LINK.findall(line), *_BACKTICK.findall(line)]
    out = []
    for c in candidates:
        c = c.split("#", 1)[0]
        if "://" in c or any(ch in c for ch in "*<>{}") or not c.startswith(config.BUNDLE_DIRS):
            continue
        if c in config.BUNDLE_DIRS:  # `references/` da solo nomina un tipo di cartella, non un allegato
            continue
        out.append(c)
    return out


def _bundled_references(doc: SkillDoc) -> list[Finding]:
    out = []
    for n, line in doc.body:
        for path in cited_paths(line):
            target = path.rstrip("/")
            exists = target in doc.files or any(f.startswith(target + "/") for f in doc.files)
            if not exists:
                out.append(Finding("R", "blocking", _loc(n), f"allegato citato ma assente: {path}"))
    return out


def _frontmatter(doc: SkillDoc) -> list[Finding]:
    out = []
    name = str(doc.frontmatter.get("name", "")).strip()
    if name != doc.dir_name:
        out.append(Finding("F", "blocking", _loc(), f"name '{name}' diverso dalla cartella '{doc.dir_name}'"))
    description = str(doc.frontmatter.get("description", "")).strip()
    if not description:
        out.append(Finding("F", "blocking", _loc(), "description mancante o vuota"))
    elif len(description) > config.MAX_DESCRIPTION_CHARS:
        out.append(
            Finding(
                "F",
                "blocking",
                _loc(),
                f"description di {len(description)} caratteri (massimo {config.MAX_DESCRIPTION_CHARS})",
            )
        )
    return out


def _size(doc: SkillDoc) -> list[Finding]:
    if len(doc.body) <= config.MAX_BODY_LINES:
        return []
    return [
        Finding(
            "S",
            "warning",
            _loc(),
            f"corpo di {len(doc.body)} righe, oltre {config.MAX_BODY_LINES}: sposta materiale negli allegati",
        )
    ]


def _maturity(doc: SkillDoc) -> list[Finding]:
    labels = {
        "example": "manca un esempio lavorato",
        "troubleshooting": "manca una sezione sui modi di guasto",
    }
    out = []
    for key, pattern in config.MATURITY_HEADINGS.items():
        if not any(pattern.search(line) for _, line in doc.body):
            out.append(Finding("M", "warning", _loc(), labels[key]))
    return out


def _licenses(doc: SkillDoc) -> list[Finding]:
    out = []
    for vendor in doc.vendor_dirs:
        prefix = f"vendor/{vendor}/"
        for required in ("LICENSE", "NOTICE"):
            if not any(f.startswith(prefix + required) for f in doc.files):
                out.append(Finding("L", "blocking", f"{prefix}", f"materiale vendorizzato senza {required}"))
    return out
