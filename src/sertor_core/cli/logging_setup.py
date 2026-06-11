"""Configurazione del logging a runtime per la CLI `sertor-rag` (US3, research D4).

Tre leve, applicate prima di eseguire il comando (così anche gli errori di config sono loggati):

- `--log-config <file>`: carica un dictConfig (JSON via stdlib, YAML se `pyyaml` è presente) e ha
  **precedenza** sulle altre leve — l'utente governa handler/appender/livelli.
- `--log-json`: un record JSON per evento su stderr (campi strutturati di `log_event`).
- `-v/--verbose`: livello `INFO` con handler umano su stderr (default `WARNING`, eventi silenziati).

Il core (`observability.logging.log_event`) emette già `extra={"operation": ..., **campi}` con i
segreti redatti: qui si configura solo livello/formato/appender (Principio IX). I nomi dei campi
sono il contratto `contracts/log-events.md`.
"""
from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path

from sertor_core.domain.errors import ConfigError

_LOGGER_NAME = "sertor_core"

# Campi strutturati emessi da `log_event` (contracts/log-events.md): vengono serializzati nel JSON.
_EXTRA_FIELDS = (
    "collection", "collections", "provider", "backend", "documents", "chunks",
    "embedding_dim", "elapsed_ms", "doc_type", "k", "results", "status", "reason", "retriable",
)

# Attributi standard di LogRecord da NON ripetere fra gli extra serializzati.
_STD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {"operation", "message", "asctime"}


class JsonLogFormatter(logging.Formatter):
    """Serializza ogni record come oggetto JSON con i campi strutturati di `log_event`.

    I segreti sono già redatti a monte (`redact()` in `log_event`, FR-022): qui non si reimplementa
    la redazione. Gli extra sconosciuti vengono inclusi se non sono attributi standard di LogRecord.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": record.created,
            "level": record.levelname,
            "operation": getattr(record, "operation", None),
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _EXTRA_FIELDS or (key not in _STD_ATTRS and not key.startswith("_")):
                payload[key] = value
        return json.dumps(payload, default=str)


def _load_dict_config(path_str: str) -> dict:
    """Legge un dictConfig da file JSON (stdlib) o YAML (richiede pyyaml). Errori → ConfigError."""
    path = Path(path_str)
    if not path.exists():
        raise ConfigError(f"--log-config: file non trovato: {path_str}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ConfigError(
                "--log-config YAML richiede pyyaml: installa pyyaml o usa un file JSON"
            ) from exc
        try:
            cfg = yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise ConfigError(f"--log-config: YAML non valido: {exc}") from exc
    else:
        try:
            cfg = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"--log-config: JSON non valido: {exc}") from exc
    if not isinstance(cfg, dict):
        raise ConfigError("--log-config: il contenuto non e' un dizionario dictConfig")
    return cfg


def setup_logging(args) -> None:
    """Configura il logger `sertor_core` secondo le leve della CLI (D4).

    Precedenza: `--log-config` (l'utente governa tutto) > `--log-json`/`-v`. Nessuna leva → livello
    `WARNING`, nessun handler aggiunto (com'e' oggi). Errori di config bloccano prima
    dell'operazione (FR-019/F9): nessun side-effect parziale.
    """
    if getattr(args, "log_config", None):
        logging.config.dictConfig(_load_dict_config(args.log_config))
        return

    logger = logging.getLogger(_LOGGER_NAME)
    if not getattr(args, "log_json", False) and not getattr(args, "verbose", False):
        logger.setLevel(logging.WARNING)  # default: eventi INFO silenziati
        return

    handler = logging.StreamHandler()  # stderr di default
    if getattr(args, "log_json", False):
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s op=%(operation)s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
