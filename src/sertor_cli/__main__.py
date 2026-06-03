"""Permette `python -m sertor_cli ...` come equivalente del comando `sertor`."""
from __future__ import annotations

import sys

from sertor_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
