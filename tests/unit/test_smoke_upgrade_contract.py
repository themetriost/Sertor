"""Offline guards on the upgrade-smoke surface (E15-FEAT-012, T007/T018/T019).

The smoke itself needs network and two full installs, so it cannot run here. What CAN be verified
offline is the **contract** of the two platform scripts — and it must be, because the claim "without
`-FromRef` nothing changed" is exactly the kind of assertion this project has paid for three times
today by asserting instead of measuring.

Text-level guards on purpose: the scripts are the single source of truth for the flow, and their
parity keeps the two platforms from drifting. These check the CONTRACT, not the behaviour.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
PS1 = (SCRIPTS / "smoke.ps1").read_text(encoding="utf-8")
SH = (SCRIPTS / "smoke.sh").read_text(encoding="utf-8")

#: The outcome list, in ONE place (FR-015). Adding one after a new field report must be one more
#: line here plus one in each script — never a restructuring.
OUTCOMES = (
    "pin-moved",
    "hook-single",
    "host-config-preserved",
    "mcp-invocation-shape",
    "no-stale-divergence",
    "version-derived-from-runtime",
    "health-green",
)


# --- T007: no regression on the install-only path -------------------------------------------------

def test_from_ref_defaults_to_empty_so_install_only_is_unchanged():
    """The upgrade flow must be OPT-IN: an existing invocation keeps its old meaning."""
    assert '[string]$FromRef = ""' in PS1, "PowerShell: -FromRef must default to empty"
    assert 'FROM_REF=""' in SH, "bash: FROM_REF must default to empty"


def test_upgrade_flow_is_gated_on_the_new_parameter():
    """Without the parameter the script must reach the pre-existing dispatch, untouched."""
    assert "if ($IsUpgrade) {" in PS1
    assert 'if [ "$IS_UPGRADE" -eq 1 ]; then' in SH
    # the original dispatch must still be there, and still reachable
    assert '"rag"  { Invoke-RagSmoke }' in PS1
    assert "rag)  rag_smoke;;" in SH


# --- T018/T019: a failure names the outcome; environment is not product -------------------------

@pytest.mark.parametrize("outcome", OUTCOMES)
def test_every_outcome_is_asserted_on_both_platforms(outcome: str):
    """Parity: an outcome verified on one platform only would hide defects on the other."""
    assert outcome in PS1, f"outcome '{outcome}' missing from smoke.ps1"
    assert outcome in SH, f"outcome '{outcome}' missing from smoke.sh"


def test_a_diverging_outcome_names_itself_and_the_context():
    """FR-008: the message carries the outcome AND where it was seen — nobody should re-run."""
    for name, text in (("ps1", PS1), ("sh", SH)):
        assert "upgrade outcome" in text, f"{name}: failure does not name the outcome"
        for field in ("assistant=", "capability=", "from=", "to="):
            assert field in text, f"{name}: failure does not carry {field}"


def test_environment_impediment_is_distinguishable_from_a_product_defect():
    """FR-011: distinct marker AND distinct exit code — a single red teaches people to ignore it."""
    assert "SMOKE_ENV" in PS1 and "exit 2" in PS1
    assert "SMOKE_ENV" in SH and "exit 2" in SH
    # and the product-defect path keeps its own marker/code
    assert "SMOKE_FAIL" in PS1 and "SMOKE_FAIL" in SH


def test_the_starting_release_is_derived_not_hardcoded():
    """Principle XIV applied to the verification: no version literal may sit in the scripts."""
    import re
    for name, text in (("ps1", PS1), ("sh", SH)):
        literals = re.findall(r"[\"'@]v\d+\.\d+\.\d+", text)
        assert not literals, (
            f"{name}: hardcoded version literal(s) {literals} — derive the ref instead"
        )


# --- the guard born from a defect this feature introduced ---------------------------------------

def test_every_needs_output_reference_names_a_declared_output():
    """A reference to a non-existent job output makes a job SKIP — silently.

    Born from a real defect in this very feature: `upgrade-smoke` was gated on
    ``needs.changes.outputs.relevant`` while the declared output is ``smoke``. GitHub Actions
    resolves the unknown name to an empty string, the `||` chain turns false, and the job is skipped
    with no error and no warning — a gate that verifies nothing while the run looks fine.

    It is the same failure shape the upgrade smoke exists to catch — an operation that succeeds and
    does nothing — and it happened *inside* the mechanism built to catch it. Hence this guard.
    """
    import re

    import yaml

    workflows = (Path(__file__).resolve().parents[2] / ".github" / "workflows")
    offenders: list[str] = []
    for path in sorted(workflows.glob("*.yml")):
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = (spec or {}).get("jobs") or {}
        declared = {
            job_id: set((job or {}).get("outputs", {}) or {})
            for job_id, job in jobs.items()
        }
        for job_id, job in jobs.items():
            for producer, name in re.findall(
                r"needs\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)",
                yaml.safe_dump(job or {}),
            ):
                if name not in declared.get(producer, set()):
                    have = sorted(declared.get(producer, set())) or "no outputs"
                    offenders.append(
                        f"{path.name}:{job_id} references "
                        f"needs.{producer}.outputs.{name}, but '{producer}' declares {have}"
                    )
    assert not offenders, "job outputs referenced but never declared:\n" + "\n".join(offenders)


def test_the_upgrade_fixture_reaches_the_state_a_real_host_is_in():
    """`health-green` must measure the HOST, not the poverty of the fixture.

    Observed on the first real run: the upgrade path never indexed, so `doctor` reported
    `index_absent` — true of the fixture and of no host that has been using the capability. The
    tempting repair was to stop asking `doctor` about the index; that is resolving by hiding, and it
    would have cost the outcome its meaning permanently.

    The guard is against the WRONG repair, not against deleting the step: deleting it goes red on
    its own. Indexing with the PREVIOUS release is also the only way to ask whether the new version
    still reads what the old one wrote — a question the install-only smoke cannot pose.
    """
    for name, text in (("ps1", PS1), ("sh", SH)):
        marker = "indexing with the PREVIOUS release"
        assert marker.lower() in text.lower(), (
            f"{name}: the upgrade flow never builds an index, so 'health-green' would measure "
            f"an empty fixture instead of a host"
        )


def test_the_version_outcome_plants_the_condition_it_claims_to_measure():
    """`version-derived-from-runtime` is vacuous unless the stamp and the lock DISAGREE.

    On this fixture both sources say the same thing, because the same ref produced the installer and
    the runtime. An assertion read against agreeing sources passes for free and measures nothing —
    the failure mode of a guard is not going red, it is going green without looking. So the script
    plants a stamp that LAGS the runtime (the field condition of E2-FEAT-021) before asking.

    Delete the planting and this guard goes red while the outcome itself would stay green: that
    inversion is the whole point of writing it down.
    """
    for name, text in (("ps1", PS1), ("sh", SH)):
        assert "0.0.1" in text, (
            f"{name}: no stale stamp is planted, so 'version-derived-from-runtime' would compare "
            f"two sources that already agree and assert nothing"
        )
        assert ".sertor-version" in text, f"{name}: the stamp file is never written"
        assert "runtime-lock" in text, (
            f"{name}: the outcome never checks WHICH source the host derived the version from"
        )


def test_the_version_outcome_stays_offline_by_seeding_the_cache():
    """The network is not under test: a GET failure must not be readable as a product divergence."""
    for name, text in (("ps1", PS1), ("sh", SH)):
        assert ".version-check.json" in text, (
            f"{name}: the version-check cache is not seeded, so the outcome depends on a live GET "
            f"and an offline runner would look like a defect"
        )
        assert "checked_at" in text, f"{name}: a cache without a fresh checked_at is not reused"


def test_the_version_outcome_cannot_write_into_a_real_project():
    """The hook honours CLAUDE_PROJECT_DIR over the event cwd — unpinned, it writes to the caller.

    Run from inside a real session (where the variable is set to the developer's own repo), the
    invocation would deposit its state THERE and read that project's lock. The fixture must own the
    variable for the duration of the call.
    """
    assert 'CLAUDE_PROJECT_DIR = $HostDir' in PS1, "ps1: the hook run is not pinned to the host"
    assert 'CLAUDE_PROJECT_DIR="$HOST"' in SH, "sh: the hook run is not pinned to the host"


def test_the_uncovered_defect_is_named_where_it_can_be_read():
    """SC-007: 'six of seven' is only honest if the seventh is written down, not left implied.

    The residual is the half of a coverage claim that rots first, because nothing breaks when it
    disappears. Two homes, both checked: the gate itself (for whoever reads why it is shaped this
    way) and the user documentation (for whoever runs `upgrade` and would otherwise trust the bare
    verb). A number without its remainder is a claim, not a measurement.
    """
    ci = (Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )
    assert "NOT COVERED" in ci, "the upgrade gate does not name the defect it leaves uncovered"
    assert "E2-FEAT-023" in ci, "the uncovered defect is not identified"

    install_doc = (Path(__file__).resolve().parents[2] / "docs/install.md").read_text(
        encoding="utf-8"
    )
    assert "10.2.1" in install_doc, "the user documentation does not describe what upgrade verifies"
    assert "The known gap" in install_doc, (
        "the user documentation does not warn about the gap, so a host would trust the bare verb"
    )
    assert "name them explicitly" in install_doc, (
        "the warning states the gap without telling the host what to do instead"
    )


def test_counting_pipelines_cannot_kill_the_script_silently():
    """A `grep | wc -l` under `set -euo pipefail` dies when the pattern is ABSENT, with no message.

    Observed on the very first real run of this gate: counting `wiki-guard` in a rag host (where it
    legitimately does not appear) made `grep` exit 1, `pipefail` failed the substitution, and
    `set -e` killed the script — returncode 1, empty stderr, no SMOKE_FAIL line.

    A gate that dies opaquely is worse than one that fails loudly, and this one exists to make
    failures name themselves. So every counting pipeline must carry an explicit fallback.
    """
    import re

    sh = (Path(__file__).resolve().parents[2] / "scripts" / "smoke.sh").read_text(encoding="utf-8")
    offenders = [
        line.strip()
        for line in sh.splitlines()
        if re.search(r"\$\(.*\|\s*wc\s+-l", line) and "||" not in line
    ]
    assert not offenders, (
        "counting pipeline lacks a `|| fallback` under pipefail:\n" + "\n".join(offenders)
    )
