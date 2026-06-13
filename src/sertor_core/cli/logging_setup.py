"""Runtime logging configuration for the `sertor-rag` CLI (US3, research D4).

Three levers, applied before executing the command (so that config errors are also logged):

- `--log-config <file>`: loads a dictConfig (JSON via stdlib, YAML if `pyyaml` is present) and
  takes **precedence** over the other levers — the user controls handlers/appenders/levels.
- `--log-json`: one JSON record per event on stderr (structured fields from `log_event`).
- `-v/--verbose`: `INFO` level with a human-readable handler on stderr
  (default `WARNING`, events silenced).

The core (`observability.logging.log_event`) already emits `extra={"operation": ..., **fields}`
with secrets redacted: only level/format/appender are configured here (Principio IX). Field names
are the contract `contracts/log-events.md`.
"""
from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path

from sertor_core.domain.errors import ConfigError

_LOGGER_NAME = "sertor_core"

# Structured fields emitted by `log_event` (contracts/log-events.md): serialized into JSON output.
_EXTRA_FIELDS = (
    "collection", "collections", "provider", "backend", "documents", "chunks",
    "embedding_dim", "elapsed_ms", "doc_type", "k", "results", "status", "reason", "retriable",
)

# Standard LogRecord attributes that must NOT be repeated among the serialized extras.
_STD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {"operation", "message", "asctime"}


class JsonLogFormatter(logging.Formatter):
    """Serializes each record as a JSON object with the structured fields of `log_event`.

    Secrets are already redacted upstream (`redact()` in `log_event`, FR-022): redaction is not
    reimplemented here. Unknown extras are included if they are not standard LogRecord attributes.
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
    """Reads a dictConfig from a JSON (stdlib) or YAML (requires pyyaml) file.

    Parse errors raise ConfigError.
    """
    path = Path(path_str)
    if not path.exists():
        raise ConfigError(f"--log-config: file not found: {path_str}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ConfigError(
                "--log-config YAML requires pyyaml: install pyyaml or use a JSON file"
            ) from exc
        try:
            cfg = yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise ConfigError(f"--log-config: invalid YAML: {exc}") from exc
    else:
        try:
            cfg = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"--log-config: invalid JSON: {exc}") from exc
    if not isinstance(cfg, dict):
        raise ConfigError("--log-config: content is not a dictConfig dictionary")
    return cfg


def setup_logging(args) -> None:
    """Configures the `sertor_core` logger according to the CLI levers (D4).

    Precedence: `--log-config` (user controls everything) > `--log-json`/`-v`. No lever →
    `WARNING` level, no handler added (current default). Config errors abort before the operation
    (FR-019/F9): no partial side effects.
    """
    if getattr(args, "log_config", None):
        logging.config.dictConfig(_load_dict_config(args.log_config))
        return

    logger = logging.getLogger(_LOGGER_NAME)
    if not getattr(args, "log_json", False) and not getattr(args, "verbose", False):
        logger.setLevel(logging.WARNING)  # default: INFO events silenced
        return

    handler = logging.StreamHandler()  # stderr by default
    if getattr(args, "log_json", False):
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s op=%(operation)s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
