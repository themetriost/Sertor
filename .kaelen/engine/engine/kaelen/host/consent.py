"""Per-file consent: from a terminal, or from an explicit list of files (specs/017 R-10).

The engine never chooses: a conflict nobody consented to refuses the operation.
"""

from __future__ import annotations

import sys


class ConsentUsage(Exception):
    """An --authorise value that is not one host-relative file (FR-016)."""


class Interaction:
    """Production: asks on stderr when stdin and stderr are both terminals."""

    def __init__(self, terminal: bool | None = None, answers=None):
        if terminal is None:
            terminal = sys.stdin.isatty() and sys.stderr.isatty()
        self.terminal = terminal
        self._answers = answers

    def ask(self, question: str) -> bool:
        if self._answers is not None:
            return self._answers(question)
        sys.stderr.write(question + " [y/N] ")
        sys.stderr.flush()
        return sys.stdin.readline().strip().lower() in ("y", "yes")


NON_INTERACTIVE = Interaction(terminal=False)


def authorised(values: list[str] | None) -> set[str]:
    out = set()
    for value in values or ():
        path = value.replace("\\", "/").strip()
        while path.startswith("./"):
            path = path[2:]
        if (
            not path
            or any(c in path for c in "*?[")
            or path.startswith("/")
            or ".." in path.split("/")
        ):
            raise ConsentUsage(f"--authorise takes one host-relative file, not {value!r}")
        out.add(path.rstrip("/"))
    return out


def decide(decisions, allowed: set[str], interaction: Interaction) -> dict[int, bool]:
    """Index of each decision -> consented. The list first, then the terminal, else no."""
    answers = {}
    for index, decision in enumerate(decisions):
        if decision.path in allowed:
            answers[index] = True
        elif interaction.terminal:
            verb = (
                "remove"
                if all(a["op"].endswith(("remove", "delete")) for a in decision.on_yes)
                else "replace"
            )
            answers[index] = interaction.ask(
                f"{verb} {decision.label}? "
                f"({decision.kind}, {decision.found}, {decision.digest_found})"
            )
        else:
            answers[index] = False
    return answers
