"""Written by Kaelen for capability 'skill-authoring'.

Runs an entry point, or a script, in the capability's environment, the folder runtime/
beside this file (specs/022, specs/026). Do not edit: the engine records this file.
"""

import subprocess
import sys
from pathlib import Path

CAPABILITY = 'skill-authoring'
ENTRY_POINTS = {"skillauthor": {"args": [], "module": "skillauthor"}}
HOME = Path(__file__).resolve().parent / "runtime"


def interpreter():
    for rel in ("env/Scripts/python.exe", "env/bin/python"):
        candidate = HOME / rel
        if candidate.is_file():
            return candidate
    return None


def main(argv):
    python = interpreter()
    if python is None or not (HOME / "kaelen-runtime.json").is_file():
        sys.stderr.write(
            "kaelen: the environment of " + CAPABILITY + " is not built on this machine; "
            "run the package's install on this repository to build it "
            "(kaelen install --host <repository> --target <assistant>)\n"
        )
        return 1
    if len(argv) >= 2 and argv[0] == "--script":
        command = [str(python), argv[1], *argv[2:]]
    elif argv and argv[0] in ENTRY_POINTS:
        entry = ENTRY_POINTS[argv[0]]
        command = [str(python), "-m", entry["module"], *entry["args"], *argv[1:]]
    else:
        known = ", ".join(sorted(ENTRY_POINTS))
        sys.stderr.write("kaelen: unknown entry point; known: " + known + "\n")
        return 64
    return subprocess.call(command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
