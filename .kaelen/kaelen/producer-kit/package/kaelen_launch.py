# Kaelen package entry for uv (specs/019-uvx-distribution/contracts/distribution.md).
# Imported from outside the package directory, it turns bytecode off before the package's
# run.py is imported, so nothing is ever written inside the package.
import sys

sys.dont_write_bytecode = True


def main():
    from kaelen_package_kaelen_producer_kit.run import main as run_main

    return run_main()
