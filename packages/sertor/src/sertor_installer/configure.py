"""Orchestration of `sertor configure` (feature 051, plan §Summary, contracts/cli-commands.md).

Thin consumer (Principio I): brings `.sertor/.env` from "empty secrets" to "ready" by resolving each
required field (flag → env/existing → prompt-if-TTY → template-default), writing additively via the
kit's `merge_env`/`_replace_key_line` (non-destructive, idempotent), then validating statically via
the SINGLE source `Settings.validate_backend()`.

**install ≠ run** (FR-015/030): never indexes, never runs `uv`/bootstrap. The optional `--check`
live probe is delegated to the vehicle `sertor-rag` in subprocess (Principio XI) and degrades
honestly when that subcommand is not yet available (US5 — Should).
"""
from __future__ import annotations

import getpass
import logging
import os
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError
from sertor_install_kit.command_runner import CommandRunner
from sertor_install_kit.env_merge import _replace_key_line, merge_env
from sertor_install_kit.observability import log_event
from sertor_installer.configure_fields import FIELD_CATALOG, ConfigField, FieldStatus, mask_secret
from sertor_installer.configure_report import (
    ConfigProfile,
    ConfigureReport,
    FieldResolution,
    LiveCheckOutcome,
    ValidationOutcome,
)
from sertor_installer.rag_profile import sanitize_corpus
from sertor_installer.resources import read_asset_text

_SERTOR_DIR = ".sertor"
_ENV_NAME = ".env"
_SERTOR_RAG = "sertor-rag"


# --- T-200: scaffold -----------------------------------------------------------------------------


def scaffold_env_if_absent(
    target_root: Path, backend: str, corpus: str | None = None
) -> bool:
    """Create `.sertor/.env` from the backend template if absent (install ≠ run).

    Reads `rag/env.{backend}.tmpl`, injects the sanitized corpus (folder name by default), and
    writes it via the kit's additive `merge_env`. Never starts `uv`, never builds an index
    (FR-015/030). Returns True if created, False if already present.
    """
    env_path = target_root / _SERTOR_DIR / _ENV_NAME
    if env_path.exists():
        return False
    resolved_corpus = corpus or sanitize_corpus(target_root.name)
    rendered = read_asset_text(f"rag/env.{backend}.tmpl").format(corpus=resolved_corpus)
    merge_env(env_path, rendered)
    return True


# --- T-210: per-field resolution -----------------------------------------------------------------


def _read_env_values(env_path: Path) -> dict[str, str]:
    """Parse `KEY=value` pairs from `.env` (line by line, no heavy imports). Last one wins."""
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def resolve_field(
    field: ConfigField,
    explicit_values: dict[str, str],
    env_path: Path,
    interactive: bool,
    env_values: dict[str, str] | None = None,
) -> FieldResolution:
    """Resolve a single field through the chain (research Punto 1).

    1. `explicit_values` (from --set / --backend / --store)  → SET, source="flag".
    2. Non-empty value already in `.env` (existing)           → KEPT, source="existing".
    3. Non-empty value in the process environment             → SET, source="env".
    4. Non-secret default from `field.default`                → SET, source="template-default".
    5. Prompt (ONLY if interactive; getpass for secrets)      → SET, source="prompt".
    6. Nothing                                                → MISSING, value=None.

    **Invariant**: never a prompt when `interactive=False` (CI-safe, FR-004/005). The order puts
    the existing `.env` value before a non-secret default so a re-run keeps the user's value.
    """
    name = field.name
    if name in explicit_values and explicit_values[name].strip():
        return FieldResolution(field, explicit_values[name].strip(), FieldStatus.SET, "flag")

    existing = env_values if env_values is not None else _read_env_values(env_path)
    if existing.get(name, "").strip():
        return FieldResolution(field, existing[name].strip(), FieldStatus.KEPT, "existing")

    env_val = os.getenv(name, "")
    if env_val.strip():
        return FieldResolution(field, env_val.strip(), FieldStatus.SET, "env")

    if not field.secret and field.default:
        return FieldResolution(field, field.default, FieldStatus.SET, "template-default")

    if interactive:
        value = _prompt_field(field)
        if value:
            return FieldResolution(field, value, FieldStatus.SET, "prompt")

    return FieldResolution(field, None, FieldStatus.MISSING, "none")


def _prompt_field(field: ConfigField) -> str:  # pragma: no cover - requires a TTY
    """Prompt for a single field (getpass for secrets). Only called when interactive (TTY)."""
    label = f"{field.name} — {field.description}"
    if field.secret:
        return getpass.getpass(f"{label}: ").strip()
    return input(f"{label}: ").strip()


# --- T-220: non-destructive write with controlled overwrite -------------------------------------


def write_resolved_fields(
    env_path: Path,
    resolutions: list[FieldResolution],
    overwrite: bool,
) -> list[FieldResolution]:
    """Write resolved fields to `.sertor/.env` additively, overwriting only on `overwrite=True`.

    - MISSING resolutions are never written (no partial configuration, FR-005).
    - A key already present with a non-empty value AND `overwrite=True` → `_replace_key_line`
      (status → OVERWRITTEN).
    - Otherwise the value is added by `merge_env` (only if not already present); an existing value
      kept without overwrite is reported as KEPT (no change).

    Re-running with the same inputs leaves `.env` byte-identical (idempotent, FR-014/SC-005).
    """
    existing = _read_env_values(env_path)
    final: list[FieldResolution] = []
    to_add: dict[str, str] = {}

    for res in resolutions:
        if res.status is FieldStatus.MISSING or res.value is None:
            final.append(res)
            continue
        name = res.field.name
        present = existing.get(name, "").strip()
        key_exists = name in existing  # the scaffold writes empty keys (e.g. `AZURE_...=`)
        if present:
            # Existing NON-EMPTY value: overwrite only on flag (non-destructive default).
            if overwrite and present != res.value:
                _overwrite_key(env_path, name, res.value)
                final.append(
                    FieldResolution(res.field, res.value, FieldStatus.OVERWRITTEN, res.source)
                )
            else:
                final.append(FieldResolution(res.field, present, FieldStatus.KEPT, "existing"))
        elif key_exists:
            # Existing EMPTY key (from the scaffold): fill it in place (not an overwrite of a value;
            # `merge_env` would skip it as "already present" → must replace the empty line).
            _overwrite_key(env_path, name, res.value)
            final.append(res)
        else:
            to_add[name] = res.value
            final.append(res)

    # Append the genuinely-absent keys via the kit's additive merge (never overwrites).
    if to_add:
        rendered = "\n".join(f"{k}={v}" for k, v in to_add.items()) + "\n"
        merge_env(env_path, rendered)

    return final


def _overwrite_key(env_path: Path, key: str, value: str) -> None:
    """Replace the `key=...` line in place, preserving everything else (kit's _replace_key_line)."""
    text = env_path.read_text(encoding="utf-8")
    env_path.write_text(_replace_key_line(text, key, f"{key}={value}"), encoding="utf-8")


# --- T-300: orchestrator -------------------------------------------------------------------------


def _settings_for_validation(backend: str, store: str, env_path: Path) -> Settings:
    """Build a `Settings` reflecting the chosen profile + the cloud fields currently in `.env`/env.

    Static, pure read (Principio XI clarification): no `Settings.load()` (which would mutate
    `os.environ` via `load_dotenv(override=True)`); instead reads the `.env` file directly and the
    process environment, so calling `validate_backend()` has no global side-effect.
    """
    file_values = _read_env_values(env_path)

    def _val(name: str) -> str:
        return (file_values.get(name) or os.getenv(name, "")).strip()

    return Settings(
        backend=backend,
        store_backend=store,
        azure_openai_endpoint=_val("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=_val("AZURE_OPENAI_API_KEY"),
        azure_openai_embed_deployment=_val("AZURE_OPENAI_EMBED_DEPLOYMENT"),
        azure_search_endpoint=_val("AZURE_SEARCH_ENDPOINT"),
        azure_search_api_key=_val("AZURE_SEARCH_API_KEY"),
    )


def _applicable_fields(backend: str, store: str) -> list[ConfigField]:
    """ALL fields the profile needs (set or not), from the SINGLE source `validate_backend()`.

    Asks the validator on a `Settings` with EMPTY cloud fields, so it emits every name the profile
    requires (not only the currently-missing ones). This drives resolution AND overwrite of values
    already present; the post-write `validate_backend()` (on real values) decides completeness.
    """
    settings = Settings(backend=backend, store_backend=store)
    return [FIELD_CATALOG[name] for name in settings.validate_backend()]


def _resolve_store(store: str | None, backend: str, env_path: Path) -> str:
    """Resolve store: explicit --store wins; else the value scaffolded in `.env`; else backend."""
    if store is not None:
        return store
    env_store = _read_env_values(env_path).get("SERTOR_STORE_BACKEND", "").strip()
    return env_store or backend


def configure_rag(
    target_root: Path,
    backend: str,
    store: str | None,
    explicit_values: dict[str, str],
    overwrite: bool,
    interactive: bool,
    check: bool,
    runner: CommandRunner | None = None,
) -> ConfigureReport:
    """Main flow: scaffold → resolve → write → validate → [probe] → report (contracts §2/3/4).

    `store=None` means "not chosen on the CLI": it is resolved from the scaffolded `.env`/template
    (the azure template defaults the store to `local` — the documented Azure-embeddings + local
    Chroma case), falling back to `backend`. An explicit `--store` always wins.
    """
    scaffold_env_if_absent(target_root, backend)
    env_path = target_root / _SERTOR_DIR / _ENV_NAME
    store = _resolve_store(store, backend, env_path)
    profile = ConfigProfile(backend, store)

    # Ensure the chosen backend/store are written too (a re-run with a different profile updates
    # them when --overwrite is given; merge_env adds them when absent).
    explicit_values = dict(explicit_values)
    explicit_values.setdefault("RAG_BACKEND", backend)
    explicit_values.setdefault("SERTOR_STORE_BACKEND", store)

    fields = _applicable_fields(backend, store)
    env_values = _read_env_values(env_path)
    resolutions = [
        resolve_field(f, explicit_values, env_path, interactive, env_values) for f in fields
    ]

    # No partial state: a required field unresolved without a TTY → error that names them, no write.
    missing_now = [r.field.name for r in resolutions if r.status is FieldStatus.MISSING]
    if missing_now and not interactive:
        raise ConfigError(
            "missing required configuration value(s) and no TTY for prompting: "
            + ", ".join(missing_now)
            + " (provide via --set KEY=VALUE or the environment, or run with a terminal)",
            key=missing_now[0],
        )

    # Write the backend/store knobs (additive) + the resolved required fields.
    _write_profile_knobs(env_path, backend, store, overwrite)
    final = write_resolved_fields(env_path, resolutions, overwrite)

    # Static validation from the SINGLE source, post-write (contracts §4).
    post = _settings_for_validation(backend, store, env_path)
    missing = tuple(post.validate_backend())
    validation = ValidationOutcome(complete=not missing, missing=missing)

    live_check = (
        _probe_live(target_root, runner)
        if check
        else LiveCheckOutcome(requested=False, ok=None, detail="")
    )

    notes = _build_notes(final)
    report = ConfigureReport(
        target=str(target_root),
        profile=profile,
        fields=tuple(final),
        validation=validation,
        live_check=live_check,
        env_path=str(env_path),
        notes=notes,
    )
    _emit_event(report)
    return report


def _write_profile_knobs(env_path: Path, backend: str, store: str, overwrite: bool) -> None:
    """Ensure RAG_BACKEND/SERTOR_STORE_BACKEND reflect the profile (additive; overwrite gated)."""
    existing = _read_env_values(env_path)
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    to_add: dict[str, str] = {}
    for key, val in (("RAG_BACKEND", backend), ("SERTOR_STORE_BACKEND", store)):
        present = existing.get(key, "").strip()
        if present:
            if overwrite and present != val:
                text = _replace_key_line(text, key, f"{key}={val}")
        else:
            to_add[key] = val
    if text and env_path.exists():
        env_path.write_text(text, encoding="utf-8")
    if to_add:
        rendered = "\n".join(f"{k}={v}" for k, v in to_add.items()) + "\n"
        merge_env(env_path, rendered)


def _build_notes(final: list[FieldResolution]) -> tuple[str, ...]:
    notes: list[str] = []
    for res in final:
        if res.status is FieldStatus.KEPT and res.source == "existing":
            notes.append(
                f"{res.field.name} preserved; use --overwrite to replace its current value"
            )
    return tuple(notes)


def _emit_event(report: ConfigureReport) -> None:
    """Observability (Principio IX, contracts §8): one event, counts only, never secrets."""
    counts: dict[str, int] = {}
    for res in report.fields:
        counts[res.status.value] = counts.get(res.status.value, 0) + 1
    log_event(
        logging.INFO,
        "configure",
        backend=report.profile.backend,
        store=report.profile.store,
        n_set=counts.get("set", 0),
        n_kept=counts.get("kept", 0) + counts.get("overwritten", 0),
        n_missing=counts.get("missing", 0),
        complete=report.validation.complete,
        live_check=report.live_check.ok if report.live_check.requested else "skip",
    )


# --- T-400/T-700: live probe (US5 — Should, deferred) -------------------------------------------


def _probe_live(target_root: Path, runner: CommandRunner | None) -> LiveCheckOutcome:
    """Live probe via the vehicle `sertor-rag check` in subprocess (Princ. XI — NOT build_embedder).

    US5 is Should/DEFERRED: `sertor-rag check` is not yet in `sertor-core`. The extension point is
    in place and degrades HONESTLY:
    - subcommand absent / "unknown command" (exit 2) → ok=None, "probe live non disponibile ...".
    - exit 0 → ok=True.
    - exit non-0 with an actionable message → ok=False, detail = the subprocess message.
    When `sertor-rag check` lands, this works unchanged (only the degradation branch becomes dead).
    """
    if runner is None:
        from sertor_installer.command_runner import SubprocessRunner

        runner = SubprocessRunner()

    if not runner.is_available(_SERTOR_RAG):
        return LiveCheckOutcome(
            requested=True,
            ok=None,
            detail=(
                "probe live non disponibile in questa versione del runtime "
                "(sertor-rag non trovato sul PATH)"
            ),
        )
    res = runner.run([_SERTOR_RAG, "check"], cwd=target_root)
    if res.returncode == 2 or "unknown command" in (res.stderr or "").lower():
        return LiveCheckOutcome(
            requested=True,
            ok=None,
            detail=(
                "probe live non disponibile in questa versione del runtime "
                "(sertor-rag check non trovato)"
            ),
        )
    if res.ok:
        return LiveCheckOutcome(requested=True, ok=True, detail="")
    detail = (res.stderr or res.stdout or "").strip() or f"exit {res.returncode}"
    return LiveCheckOutcome(requested=True, ok=False, detail=mask_secret_free(detail))


def mask_secret_free(text: str) -> str:
    """Defence-in-depth: never echo a value that looks like a secret out of the subprocess."""
    return mask_secret(text) if text.lower().startswith("sk-") else text
