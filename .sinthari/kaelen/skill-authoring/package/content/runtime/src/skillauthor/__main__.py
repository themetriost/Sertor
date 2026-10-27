"""`python -m skillauthor`: il punto d'ingresso che usa il launcher di Kaelen sugli ospiti."""

import sys

from .cli import main

sys.exit(main())
