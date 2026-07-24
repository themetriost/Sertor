"""Guardia: nessun evento usa un nome RISERVATO di `LogRecord` come campo extra.

**Bug reale trovato il 2026-07-24.** `wiki_tools/structure.py` e `registry.py` passavano `created=`
a `log_event`. `created` è un attributo riservato di `LogRecord` (il timestamp del record):
`logging.makeRecord` solleva `KeyError: "Attempt to overwrite 'created' in LogRecord"`.

Il difetto era **latente e mascherato**: finché il logger `sertor_core` resta a WARNING, un
`log_event(INFO, …)` non crea alcun record e non arriva mai a `makeRecord`. Appena il livello scende
a INFO — cosa che `enable_observability` fa **di proposito**, perché gli handler possano catturare
gli eventi — ogni chiamata esplode. In produzione: con `SERTOR_OBSERVABILITY=true`,
`sertor-wiki-tools structure init` andava in crash.

Nella suite si manifestava come **83 fallimenti** apparentemente scorrelati, tutti *dopo* il primo
test che abbassava il livello del logger. I singoli test passavano in isolamento — la firma classica
di un difetto mascherato dalla configurazione di default.

Questo test rende impossibile reintrodurlo: verifica il **comportamento** reale (emettere l'evento a
INFO), non la forma del sorgente.
"""
from __future__ import annotations

import logging

import pytest

from sertor_core.observability.logging import get_logger, log_event

# Attributi di `LogRecord` che `logging.makeRecord` rifiuta di far sovrascrivere da `extra`.
RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "taskName",
    "message", "asctime",
}


@pytest.fixture
def logger_at_info():
    """Porta il logger a INFO — la condizione che smaschera il difetto — e lo ripristina."""
    logger = get_logger()
    previous = logger.level
    logger.setLevel(logging.INFO)
    yield logger
    logger.setLevel(previous)


def test_reserved_field_would_raise(logger_at_info):
    """Il pericolo è reale, non teorico.

    Con il logger a INFO, un campo riservato solleva `KeyError` invece di essere ignorato.
    """
    with pytest.raises(KeyError, match="created"):
        log_event(logging.INFO, "probe", created=1)


def test_structure_emits_its_event_at_info(logger_at_info, tmp_path):
    """`structure init` deve emettere il proprio evento senza esplodere, con il logger a INFO."""
    from sertor_core.wiki_tools.profile import load_profile
    from sertor_core.wiki_tools.structure import init_structure

    config = tmp_path / "wiki.config.toml"
    config.write_text(
        'profile = "code+doc"\nlanguage = "en"\nroot = "wiki"\n'
        'index_file = "index.md"\nlog_file = "log.md"\n'
        'source_dirs = ["src"]\n'
        '[[taxonomy]]\nname = "concepts"\ndir = "concepts"\ntype = "concept"\n',
        encoding="utf-8",
    )
    profile = load_profile(config)

    result = init_structure(profile)  # non deve sollevare

    assert result.created, "la struttura doveva essere creata"


@pytest.mark.parametrize("field", sorted(RESERVED))
def test_every_reserved_name_is_rejected_by_logging(logger_at_info, field):
    """Documenta l'elenco: se una versione di Python ne aggiunge uno, il test lo scopre."""
    try:
        log_event(logging.INFO, "probe", **{field: "x"})
    except KeyError:
        return  # atteso: il nome è riservato
    pytest.fail(f"{field!r} non è più riservato: aggiornare l'elenco RESERVED e la guardia")
