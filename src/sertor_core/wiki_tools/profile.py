"""`WikiProfile`: la config dell'ospite — unica fonte di specificità (Principio X, Principio VIII).

Caricata da `wiki.config.toml` con `tomllib` (stdlib, research D1). Tutta la specificità
dell'ospite (radice, tassonomia, cartelle-sorgente, lingua, profilo, stringhe) vive qui: nessun
default è hard-coded nel *corpo* delle operazioni — il profilo di Sertor è un *file esterno*
sostituibile. La validazione è esplicita (Principio IV): config assente/malformata → `ConfigError`,
mai uno stato parziale o un `None` silenzioso.
"""
from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event

# Default *di campo* (non di ospite): scelte generiche del formato wiki, non specificità del
# progetto. La specificità (root, tassonomia, source_dirs, lingua) resta obbligatoria in config.
_DEFAULT_INDEX_FILE = "index.md"
_DEFAULT_LOG_FILE = "log.md"
_DEFAULT_FRONTMATTER_REQUIRED = ("title", "type", "tags", "created", "updated")
_DEFAULT_FRONTMATTER_OPTIONAL = ("sources",)
_DEFAULT_WIKILINK_STYLE = "[[name]]"
_DEFAULT_LOG_FORMAT = "## [{date}] {op} | {title}"


@dataclass(frozen=True)
class TaxonomyEntry:
    """Una voce di tassonomia: area logica → cartella relativa → tipo di frontmatter."""

    name: str
    dir: str
    type: str


@dataclass(frozen=True)
class WikiProfile:
    """Descrizione dichiarativa dell'ospite. `config_dir` ancora i path relativi al disco."""

    config_dir: Path
    profile: str
    language: str
    root: str
    taxonomy: list[TaxonomyEntry]
    index_file: str = _DEFAULT_INDEX_FILE
    log_file: str = _DEFAULT_LOG_FILE
    source_dirs: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    frontmatter_required: list[str] = field(
        default_factory=lambda: list(_DEFAULT_FRONTMATTER_REQUIRED)
    )
    frontmatter_optional: list[str] = field(
        default_factory=lambda: list(_DEFAULT_FRONTMATTER_OPTIONAL)
    )
    wikilink_style: str = _DEFAULT_WIKILINK_STYLE
    log_format: str = _DEFAULT_LOG_FORMAT
    roles: dict[str, str] = field(default_factory=dict)
    rag: dict[str, object] = field(default_factory=dict)
    strings: dict[str, str] = field(default_factory=dict)

    @property
    def root_path(self) -> Path:
        """Radice assoluta del wiki (relativa alla cartella della config)."""
        return self.config_dir / self.root

    @property
    def index_path(self) -> Path:
        return self.root_path / self.index_file

    @property
    def log_path(self) -> Path:
        return self.root_path / self.log_file

    def existing_taxonomy(self) -> list[TaxonomyEntry]:
        """Voci di tassonomia la cui cartella esiste sul disco (dir assente → warning+skip)."""
        present: list[TaxonomyEntry] = []
        for entry in self.taxonomy:
            if (self.root_path / entry.dir).is_dir():
                present.append(entry)
            else:
                log_event(
                    logging.WARNING,
                    "profile",
                    profile=self.profile,
                    taxonomy=entry.name,
                    dir=entry.dir,
                    note="taxonomy-dir-missing-skip",
                )
        return present


def _require(value: object, key: str) -> None:
    if value is None or value == "" or value == []:
        raise ConfigError("campo di configurazione obbligatorio assente o vuoto", key=key)


def _coerce_str_list(value: object, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError("atteso un elenco di stringhe", key=key)
    return list(value)


def _parse_taxonomy(raw: object) -> list[TaxonomyEntry]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("la tassonomia deve avere almeno una voce", key="taxonomy")
    entries: list[TaxonomyEntry] = []
    seen_names: set[str] = set()
    seen_dirs: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ConfigError("voce di tassonomia malformata", key=f"taxonomy[{i}]")
        name, directory, typ = item.get("name"), item.get("dir"), item.get("type")
        for label, value in (("name", name), ("dir", directory), ("type", typ)):
            if not isinstance(value, str) or not value:
                raise ConfigError("voce di tassonomia incompleta", key=f"taxonomy[{i}].{label}")
        if name in seen_names or directory in seen_dirs:
            raise ConfigError("nomi/cartelle di tassonomia non univoci", key=f"taxonomy[{i}]")
        seen_names.add(name)
        seen_dirs.add(directory)
        entries.append(TaxonomyEntry(name=name, dir=directory, type=typ))
    return entries


def load_profile(config_path: str | Path, root_override: str | Path | None = None) -> WikiProfile:
    """Carica e valida `wiki.config.toml`; `ConfigError` su assente/malformata (Principio IV).

    `root_override` (stile Transcriptio `--root`) sostituisce la cartella-ospite usata per
    risolvere i path relativi, lasciando immutato il file di config.
    """
    config_path = Path(config_path)
    if not config_path.is_file():
        raise ConfigError("file di configurazione del wiki non trovato", key=str(config_path))

    try:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"configurazione TOML malformata: {exc}", key=str(config_path)) from exc

    config_dir = Path(root_override) if root_override is not None else config_path.parent

    language = data.get("language")
    root = data.get("root")
    _require(language, "language")
    _require(root, "root")
    taxonomy = _parse_taxonomy(data.get("taxonomy"))

    rag = data.get("rag") or {}
    strings = data.get("strings") or {}
    roles = data.get("roles") or {}
    if not isinstance(rag, dict) or not isinstance(strings, dict) or not isinstance(roles, dict):
        raise ConfigError("sezioni rag/strings/roles malformate", key=str(config_path))

    profile = WikiProfile(
        config_dir=config_dir,
        profile=str(data.get("profile") or "code+doc"),
        language=str(language),
        root=str(root),
        taxonomy=taxonomy,
        index_file=str(data.get("index_file") or _DEFAULT_INDEX_FILE),
        log_file=str(data.get("log_file") or _DEFAULT_LOG_FILE),
        source_dirs=_coerce_str_list(data.get("source_dirs"), "source_dirs"),
        exclude=_coerce_str_list(data.get("exclude"), "exclude"),
        frontmatter_required=(
            _coerce_str_list(data.get("frontmatter_required"), "frontmatter_required")
            or list(_DEFAULT_FRONTMATTER_REQUIRED)
        ),
        frontmatter_optional=(
            _coerce_str_list(data.get("frontmatter_optional"), "frontmatter_optional")
            or list(_DEFAULT_FRONTMATTER_OPTIONAL)
        ),
        wikilink_style=str(data.get("wikilink_style") or _DEFAULT_WIKILINK_STYLE),
        log_format=str(data.get("log_format") or _DEFAULT_LOG_FORMAT),
        roles={str(k): str(v) for k, v in roles.items()},
        rag=dict(rag),
        strings={str(k): str(v) for k, v in strings.items()},
    )
    log_event(
        logging.INFO,
        "profile",
        profile=profile.profile,
        language=profile.language,
        root=profile.root,
        taxonomy_count=len(profile.taxonomy),
        source_dirs=len(profile.source_dirs),
    )
    return profile
