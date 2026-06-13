"""Synthetic mini-corpus for the 10 chunker languages (FEAT-005, FR-003).

CLOSED and versioned corpus: for each language a minimal source with a function that calls
another one (plus import/inheritance for Python, where declared in `COVERAGE`). Here the
ground-truth is TOTAL: measures full precision (SC-002) and verifies that declared coverage
is true (no untested promises). It is also the SC-007 verification: a corpus different from
sertor, zero engine adaptations (fix analyze C1).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageCase:
    language: str
    filename: str
    source: str
    caller_qual: str      # qualname of the expected caller
    callee_name: str      # name of the called symbol


LANGUAGE_CASES: tuple[LanguageCase, ...] = (
    LanguageCase("python", "mod_b.py",
                 "import mod_a\n\n\ndef runner():\n    return aiutante()\n",
                 "runner", "aiutante"),
    LanguageCase("javascript", "app.js",
                 "function aiutante() { return 1; }\n"
                 "function runner() { return aiutante(); }\n",
                 "runner", "aiutante"),
    LanguageCase("typescript", "app.ts",
                 "function aiutante(): number { return 1; }\n"
                 "function runner(): number { return aiutante(); }\n",
                 "runner", "aiutante"),
    LanguageCase("java", "App.java",
                 "class App {\n"
                 "    int aiutante() { return 1; }\n"
                 "    int runner() { return aiutante(); }\n"
                 "}\n",
                 "App.runner", "aiutante"),
    LanguageCase("c_sharp", "App.cs",
                 "class App {\n"
                 "    int Aiutante() { return 1; }\n"
                 "    int Runner() { return Aiutante(); }\n"
                 "}\n",
                 "App.Runner", "Aiutante"),
    LanguageCase("go", "app.go",
                 "package main\n\n"
                 "func aiutante() int { return 1 }\n\n"
                 "func runner() int { return aiutante() }\n",
                 "runner", "aiutante"),
    LanguageCase("c", "app.c",
                 "int aiutante() { return 1; }\n"
                 "int runner() { return aiutante(); }\n",
                 "runner", "aiutante"),
    LanguageCase("cpp", "app.cpp",
                 "int aiutante() { return 1; }\n"
                 "int runner() { return aiutante(); }\n",
                 "runner", "aiutante"),
    LanguageCase("php", "app.php",
                 "<?php\n"
                 "function aiutante() { return 1; }\n"
                 "function runner() { return aiutante(); }\n",
                 "runner", "aiutante"),
    LanguageCase("ruby", "app.rb",
                 "def aiutante\n  1\nend\n\n"
                 "def runner\n  aiutante()\nend\n",
                 "runner", "aiutante"),
)

# Additional Python source: defines the callee + base class (for imports/inherits).
PYTHON_COMPANION = (
    "mod_a.py",
    "class Base:\n"
    "    pass\n\n\n"
    "class Figlia(Base):\n"
    "    pass\n\n\n"
    "def aiutante():\n"
    "    return 1\n",
)
