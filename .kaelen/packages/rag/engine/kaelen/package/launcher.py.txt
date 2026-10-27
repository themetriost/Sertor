# Kaelen package launcher (specs/015-packaging-injection/contracts/package.md).
# Identical in every package: it starts the engine carried in ./engine, whatever else is
# installed on this machine. Written for any Python 3 so that an old interpreter is refused
# with a message instead of a syntax error.
import os
import sys

REQUIRED = (3, 11)
RUNTIME_UNAVAILABLE = 69


def main():
    found = tuple(sys.version_info[:2])
    if found < REQUIRED:
        sys.stderr.write(
            "kaelen package needs Python >= %d.%d, found %d.%d\n" % (REQUIRED + found)
        )
        return RUNTIME_UNAVAILABLE
    # The package leaves nothing behind, not even bytecode caches inside itself (V-3).
    sys.dont_write_bytecode = True
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "engine"))
    from kaelen.cli import main as kaelen_main

    return kaelen_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
