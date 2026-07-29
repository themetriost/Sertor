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
