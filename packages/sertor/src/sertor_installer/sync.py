"""Sync degli assets verso `.claude/` del repo di sviluppo (D2).

Fonte canonica = gli assets nel pacchetto; `.claude/` del repo è il **derivato**. Questo script,
*in sviluppo*, propaga `assets/claude/**` → `.claude/**` così il dogfood gira sulla versione
installabile. Direzione canonica: **assets → .claude** (mai il contrario). Il test di guardia
`tests/unit/test_assets_sync.py` impedisce che le due copie divergano (drift = errore CI).

Uso: `python -m sertor_installer.sync [--repo-root <path>] [--dry-run]`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sertor_installer.resources import iter_asset_dir


def sync_assets_to_claude(repo_root: Path, dry_run: bool = False) -> dict[str, str]:
    """Copia `assets/claude/**` verso `<repo_root>/.claude/`. Ritorna `{rel: stato}`.

    Stato ∈ `created` (file nuovo) · `updated` (contenuto diverso) · `identical` (nessuna modifica).
    In `dry_run` non scrive nulla, riporta solo cosa farebbe.
    """
    result: dict[str, str] = {}
    claude_root = repo_root / ".claude"

    for rel_path, content in iter_asset_dir("claude"):
        dest = claude_root / rel_path
        if not dest.exists():
            status = "created"
        elif dest.read_text(encoding="utf-8") == content:
            status = "identical"
        else:
            status = "updated"
        result[rel_path] = status
        if status != "identical" and not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sertor_installer.sync",
        description="Propaga gli assets bundlati al .claude/ del repo (sviluppo, D2).",
    )
    parser.add_argument(
        "--repo-root", default=".", help="radice del repo di sviluppo (default: cwd)"
    )
    parser.add_argument("--dry-run", action="store_true", help="non scrive, riporta soltanto")
    args = parser.parse_args(argv)

    result = sync_assets_to_claude(Path(args.repo_root).resolve(), dry_run=args.dry_run)
    for rel, status in sorted(result.items()):
        print(f"  {status:<10}{rel}")
    n_changed = sum(1 for s in result.values() if s != "identical")
    print(f"Sync: {n_changed} file {'da aggiornare' if args.dry_run else 'aggiornati'}, "
          f"{len(result)} totali")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
