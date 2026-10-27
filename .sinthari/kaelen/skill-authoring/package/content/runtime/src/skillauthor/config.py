"""Configurazione centralizzata (Principio IX): soglie e default in un solo posto."""

from __future__ import annotations

import re

MAX_BODY_LINES = 500
MAX_DESCRIPTION_CHARS = 1024

DEFAULT_CASES = 3
DEFAULT_RUNS = 1
CONFIGS = ("with_skill", "without_skill")

# Cartelle di allegati: un percorso citato nel corpo che inizia così deve esistere nella skill.
BUNDLE_DIRS = ("references/", "scripts/", "assets/", "templates/", "evals/", "vendor/")

# Percorsi propri di un assistente: nel corpo rendono la skill non host-agnostica.
HOST_PATH_PATTERNS = (
    re.compile(r"(?<![\w.])\.claude/"),
    re.compile(r"(?<![\w.])\.github/"),
    re.compile(r"(?<![\w.])\.agents/"),
    re.compile(r"(?<![\w.])\.codex/"),
    re.compile(r"~/\.claude\b"),
)

# Invocazione slash: a inizio riga, o da sola fra backtick. Non tocca /dev/null né gli URL, né un
# backtick di chiusura seguito da testo (`ops/query.md`/lint, emerso su un agente reale nella 005).
SLASH_PATTERN = re.compile(r"^\s*/[a-z][\w-]*(?=`|\s|$)|`/[a-z][\w-]*`")

# Titoli (heading) che contano come esempio lavorato e come sezione sui modi di guasto (lint M).
MATURITY_HEADINGS = {
    "example": re.compile(r"^#{1,6}\s.*\b(esemp\w*|example\w*|worked)", re.IGNORECASE),
    "troubleshooting": re.compile(
        r"^#{1,6}\s.*\b(guast\w*|troubleshoot\w*|failure|errori comuni|quando qualcosa)", re.IGNORECASE
    ),
}

PARITY_IGNORE = ("__pycache__",)

# --- Agenti (feature 005, research R2, R4, R6) --------------------------------------------

# Forme d'agente che Kaelen colloca: il suffisso decide la forma. `.agent.md` prima di `.md`.
AGENT_SUFFIXES = ((".agent.md", "markdown"), (".md", "markdown"), (".toml", "toml"))

AGENT_TARGETS = ("claude-code", "github-copilot", "codex")

# Come ogni assistente rappresenta i campi d'intestazione noti. Un campo non in tabella vale `unknown`,
# tranne su Codex, dove il wrapper `codex-agent-toml` porta solo name, description e il prompt.
PARITY_REFERENCE = "kaelen 0.16.1 placement"
AGENT_PARITY = {
    "claude-code": {
        "name": "represented",
        "description": "represented",
        "tools": "represented",
        "model": "represented",
    },
    "github-copilot": {
        "name": "represented",
        "description": "represented",
        "tools": "different",
        "model": "different",
    },
    "codex": {"name": "represented", "description": "represented"},
}
PARITY_DEFAULT = {"claude-code": "unknown", "github-copilot": "unknown", "codex": "dropped"}

# Regola T (R12): i sistemi operativi su cui ogni strumento shell di Claude Code è garantito. `Bash` gira
# anche su Windows, ma solo se la macchina ha bash: non è garantito, e senza bash l'ospite espone solo
# `PowerShell`. Vale per il vocabolario di Claude Code: Copilot ne ha un altro, Codex non riceve `tools`.
OPERATING_SYSTEMS = ("linux", "macos", "windows")
SHELL_TOOLS = {"Bash": ("linux", "macos"), "PowerShell": ("windows",)}

# Skill nominate dal prompt: un nome fra backtick, o con un trattino, accanto alla parola «skill».
# Le prime due forme (backtick) sono una citazione; le altre due un'euristica, che può sbagliare
# ("della skill ad-hoc"): per questo un nome trovato solo così, se assente, è un avviso e non un bloccante.
_SKILL_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_HYPHENATED = r"[a-z0-9]+(?:-[a-z0-9]+)+"
SKILL_NAME_PATTERNS = (
    ("backtick", re.compile(rf"\bskill\s+`({_SKILL_NAME})`")),
    ("backtick", re.compile(rf"`({_SKILL_NAME})`\s+skill\b")),
    ("plain", re.compile(rf"\bskill\s+({_HYPHENATED})\b")),
    ("plain", re.compile(rf"(?<![\w`-])({_HYPHENATED})\s+skill\b")),
)
