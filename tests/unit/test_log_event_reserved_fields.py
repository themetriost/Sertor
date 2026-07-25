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
import sys

import pytest

from sertor_core.observability.logging import get_logger, log_event

# Attributi di `LogRecord` che `logging.makeRecord` rifiuta di far sovrascrivere da `extra`.
#
# **Derivati dal runtime, non scritti a mano.** La prima versione elencava i nomi a mano, incluso
# `taskName` — che esiste **solo da Python 3.12**: sotto 3.11 il test falliva chiedendo di
# «aggiornare l'elenco», e la CI di `master` è rimasta rossa dal 2026-07-24 al 07-25. Un elenco
# hardcoded è **la stessa classe di difetto** che questa guardia presidia (uno stato scritto a parte
# invece che derivato dalla realtà, cfr. E2-FEAT-021): qui la realtà è l'interprete che gira.
_SPECIAL = {"message", "asctime"}  # non attributi del record: li aggiunge la formattazione


def _reserved_names() -> set[str]:
    """I nomi che QUESTO interprete considera riservati, letti da un `LogRecord` reale."""
    probe = logging.LogRecord("n", logging.INFO, "p", 1, "m", None, None)
    return set(vars(probe)) | _SPECIAL


RESERVED = _reserved_names()

# I nomi che ci aspettiamo di trovare. Serve a scoprire il caso opposto: una versione di Python che
# **aggiunge** un attributo riservato — cosa che 3.12 ha fatto con `taskName`. È un elenco di
# riferimento, non la fonte del parametrizzato.
KNOWN = {
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
    """Ogni nome riservato DA QUESTO interprete deve essere rifiutato, non ignorato in silenzio."""
    try:
        log_event(logging.INFO, "probe", **{field: "x"})
    except KeyError:
        return  # atteso: il nome è riservato
    pytest.fail(f"{field!r} è riservato ma `log_event` lo accetta: la guardia non protegge più")


def test_new_reserved_names_are_surfaced():
    """Se una versione di Python **aggiunge** un attributo riservato, si deve sapere.

    È il motivo per cui l'elenco `KNOWN` sopravvive alla derivazione: la lista non serve più a
    guidare il parametrizzato (lo fa il runtime), ma a rendere **visibile** una novità
    dell'interprete invece di assorbirla in silenzio — un nome nuovo diventa un campo che nessun
    evento può più usare, e la scoperta non deve arrivare da un crash in produzione.
    """
    unexpected = RESERVED - KNOWN
    assert not unexpected, (
        f"Python {'.'.join(map(str, sys.version_info[:2]))} riserva nomi non previsti: "
        f"{sorted(unexpected)} — verificare che nessun evento li usi e aggiornarli in KNOWN"
    )
