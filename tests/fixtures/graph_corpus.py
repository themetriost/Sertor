"""Mini-corpus sintetico per i 10 linguaggi del chunker (FEAT-005, FR-003).

Corpus CHIUSO e versionato: per ogni linguaggio un sorgente minimo con una funzione che ne
chiama un'altra (più import/ereditarietà per Python, dove dichiarati in `COVERAGE`). Qui il
ground-truth è TOTALE: misura la precisione piena (SC-002) e verifica che la copertura
dichiarata sia vera (mai promessa non testata). È anche la verifica SC-007: un corpus diverso
da sertor, zero adattamenti del motore (fix analyze C1).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageCase:
    language: str
    filename: str
    source: str
    caller_qual: str      # qualname del chiamante atteso
    callee_name: str      # nome del simbolo chiamato


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

# Sorgente Python aggiuntivo: definisce il chiamato + classe base (per imports/inherits).
PYTHON_COMPANION = (
    "mod_a.py",
    "class Base:\n"
    "    pass\n\n\n"
    "class Figlia(Base):\n"
    "    pass\n\n\n"
    "def aiutante():\n"
    "    return 1\n",
)
