"""Guard (NRT): the UX assets teach HOST-AWARE install (`--assistant <host>`) for rag/wiki/flow.

E12-FEAT-012 — real dogfood bug: the agentic UX layer (`guided-setup` skill, `concierge` agent)
guided installs WITHOUT determining the host, so on a GitHub Copilot CLI host it invoked
`sertor install …` / `sertor-flow install` with no `--assistant` → the installer default (`claude`)
laid down the WRONG layout. The installer itself honours `--assistant` (covered by the smoke E2E);
this NRT covers the gap the smoke cannot: that the **UX assets instruct the agent to pass the right
`--assistant`**. It is a text/lint guard on the instructions (it cannot prove the agent does so at
runtime — that needs a live host) and fails if a regression:

  (a) drops the host-detection rule from `guided-setup`/`concierge`;
  (b) shows an install command (`uvx … sertor install rag/wiki`, `… sertor-flow install`) WITHOUT
      `--assistant`, or drops a capability (rag/wiki/flow) from the host-aware install guidance;
  (c) re-marks `--assistant` as *optional* (the exact pre-fix phrasing was "optionally add
      `--assistant`").

Name-citations in prose (e.g. "installed by `sertor install rag`", or line listing
`sertor install rag`, `sertor configure --set`) are NOT install command lines and must not be
flagged — hence (b) keys on the real `uvx … install …` command span, and (b2) on the exact
"<verb> --assistant" pairing rather than a naive "line has a `--` flag" heuristic.
"""
from __future__ import annotations

import re

from sertor_installer.resources import read_asset_text

_GUIDED_SETUP = "rag/skills/guided-setup/SKILL.md"
_CONCIERGE = "rag/agents/concierge.md"
_UX_ASSETS = (_GUIDED_SETUP, _CONCIERGE)

# The three install verbs the UX layer guides — each MUST be taught with `--assistant`.
_INSTALL_VERBS = ("sertor install rag", "sertor install wiki", "sertor-flow install")

# A real install COMMAND span: an `uvx …` invocation that reaches an install verb (the canonical
# form the UX assets show). Bounded by backticks (the commands live in backtick spans), so prose
# name-citations like "installed by `sertor install rag`" (no `uvx`) never match.
_UVX_INSTALL = re.compile(
    r"uvx [^`]*?(?:sertor install (?:rag|wiki)|sertor-flow install)[^`]*"
)


def _norm(asset: str) -> str:
    """Asset text with whitespace collapsed (so a line-wrapped command reads as one span)."""
    return re.sub(r"\s+", " ", read_asset_text(asset))


# --- (a) the host-detection rule is present ---------------------------------------------------


def test_guided_setup_teaches_host_detection():
    """`guided-setup` carries the host-detection step and the `--assistant` rule."""
    body = read_asset_text(_GUIDED_SETUP)
    assert "--assistant" in body
    assert re.search(r"[Dd]etect the host", body), "missing the 'Detect the host' step"


def test_concierge_teaches_host_aware_install():
    """`concierge` carries the host-aware-install rule (detect host → pass `--assistant`)."""
    body = read_asset_text(_CONCIERGE)
    low = body.lower()
    assert "--assistant" in body
    assert "host-aware install" in low or "detect the host" in low


# --- (b) each capability is taught WITH the flag (wiki/flow cannot silently drop) -------------


def test_guided_setup_each_capability_carries_assistant():
    """Each of rag/wiki/flow appears as `<verb> --assistant` in `guided-setup` (no capability
    is shown without the flag)."""
    body = _norm(_GUIDED_SETUP)
    missing = [v for v in _INSTALL_VERBS if f"{v} --assistant" not in body]
    assert not missing, f"install verb(s) shown without `--assistant` in guided-setup: {missing}"


# --- (b2) no real `uvx … install …` command span omits `--assistant` -------------------------


def _uvx_installs_without_assistant(asset: str) -> list[str]:
    return [
        m.group(0)
        for m in _UVX_INSTALL.finditer(_norm(asset))
        if "--assistant" not in m.group(0)
    ]


def test_no_uvx_install_command_without_assistant():
    """Every `uvx … install …` command span in the UX assets carries `--assistant`."""
    found = {a: o for a in _UX_ASSETS if (o := _uvx_installs_without_assistant(a))}
    assert not found, f"uvx install command(s) missing `--assistant`: {found}"


# --- (c) `--assistant` is never re-marked optional --------------------------------------------


def test_assistant_never_optional():
    """The pre-fix anti-pattern ('optionally add `--assistant`') must not reappear."""
    for asset in _UX_ASSETS:
        body = _norm(asset)
        assert not re.search(r"optional[a-z]*\W+(?:add\W+)?`?--assistant", body), (
            f"`--assistant` presented as optional in {asset}"
        )
        assert not re.search(r"`?--assistant`?\W+\(?optional", body), (
            f"`--assistant` presented as optional in {asset}"
        )


# --- meta: the detector is neither vacuous nor over-eager -------------------------------------


def test_uvx_install_detector_flags_missing_and_passes_present():
    """Positive/negative: a bare `uvx … install` is flagged; one with `--assistant` passes."""
    bad = re.sub(r"\s+", " ", "run `uvx --from x sertor install wiki --backend local` now")
    m_bad = _UVX_INSTALL.search(bad)
    assert m_bad is not None and "--assistant" not in m_bad.group(0)

    good = re.sub(r"\s+", " ", "run `uvx --from x sertor install wiki --assistant copilot-cli` now")
    m_good = _UVX_INSTALL.search(good)
    assert m_good is not None and "--assistant" in m_good.group(0)


def test_prose_name_citation_is_not_flagged():
    """A prose name-citation (no `uvx`, no flag) is not an install command → not matched."""
    prose = re.sub(r"\s+", " ", "the runtime is installed by `sertor install rag` into .sertor")
    assert _UVX_INSTALL.search(prose) is None
