"""Configurazione dell'osservabilità della CLI (REQ-050/051/052).

Rende visibili i log strutturati del core (logger `sertor_core`, di default muto) e li collega ad
appender esterni. Precedenza: `--log-config` (dictConfig YAML/JSON) prevale; altrimenti
`-v`/`--log-json` configurano un handler base. Formatter JSON interno (nessuna dipendenza).
"""
from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path

_LOGGER = "sertor_core"
# Attributi standard di LogRecord da escludere quando si serializzano i campi strutturati.
_STD = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime", "taskName"}


class _JsonFormatter(logging.Formatter):
    """Serializza ogni record come JSON: livello, logger, messaggio + campi strutturati."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in _STD and not k.startswith("_"):
                payload[k] = v
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure(verbose: bool = False, log_json: bool = False, log_config: str | None = None) -> None:
    """Configura il logging della CLI in base alle opzioni globali."""
    if log_config:
        _load_config_file(log_config)
        return
    logger = logging.getLogger(_LOGGER)
    logger.setLevel(logging.INFO if verbose else logging.WARNING)
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter() if log_json else logging.Formatter("%(message)s"))
    logger.handlers = [handler]
    logger.propagate = False


def _load_config_file(path: str) -> None:
    """Carica una configurazione di logging dictConfig da file YAML o JSON (DA-C3)."""
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith((".yaml", ".yml")):
        import yaml

        config = yaml.safe_load(text)
    else:
        config = json.loads(text)
    logging.config.dictConfig(config)
