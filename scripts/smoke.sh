#!/usr/bin/env bash
# End-to-end smoke test of a Sertor capability on a host, against the real distribution (git+url@master).
#
# Installs a Sertor capability into a host directory exactly as a third-party project would
# (`uvx --from git+url#subdirectory=packages/<pkg> <verb> ...`) for a chosen assistant, then asserts
# the deposited artifacts (and, for `rag`, drives the runtime CLI end-to-end: index -> doctor ->
# search). It catches integration bugs the offline suite cannot (CLI discoverability, cwd/index
# anchoring, per-assistant asset routing), because it drives the real installed entry-points from a
# clean host.
#
# MATRIX: {claude, copilot-cli} x {rag, wiki, flow}.
#   * rag   — `sertor install rag`   : .sertor/ + .mcp.json + UX assets, then index/doctor/search.
#   * wiki  — `sertor install wiki`  : wiki-author skill, wiki-curator agent, hooks, wiki.config.toml,
#             wiki/ scaffold, the SERTOR:WIKI-RITUAL block (deposit-only, no runtime).
#   * flow  — `sertor-flow install`  : SpecKit (via `specify init`, NETWORK), constitution starter,
#             requirements/configuration-manager surfaces, the SERTOR:SDLC-RITUAL block (deposit-only).
#
# ISOLATION (no "Sertor on Sertor"): the smoke runs in a host directory OUTSIDE the Sertor checkout,
# with an environment scrubbed of inherited SERTOR_* variables, and launches `uvx` with
# cwd = the host dir plus UV_NO_WORKSPACE=1 so `uv` cannot discover the local workspace. For `rag`
# this also guarantees `sertor-core` is BUILT FROM GIT (asserted against .sertor/uv.lock). `wiki`/
# `flow` do not create `.sertor`, so their isolation is host-outside-the-checkout + install-from-git.
#
# FIXTURE vs REAL TARGET: by DEFAULT (no TARGET) the smoke creates a NEUTRAL synthetic project
# (README.md + src/app.py + src/utils.ts — a generic project, never Sertor files) in a temp dir and
# cleans it up. With a TARGET the smoke runs on THAT existing repo (and does NOT delete it). CI uses
# a real target only for `rag` (PgnToFen); `wiki`/`flow` use the synthetic fixture.
#
# Provider (rag) = `hash` (zero-credentials, zero-download, deterministic). The install writes
# SERTOR_EMBED_PROVIDER=glove into .sertor/.env (would download ~822 MB), so the script rewrites
# that line to `hash` before any runtime command. `--no-rerank --no-graph` keep the venv slim.
#
# On success prints a single machine-checkable marker and exits 0:
#     SMOKE_OK assistant=<a> capability=<c> ...<capability fields>...
# On any failed assertion prints `SMOKE_FAIL: <reason>` and exits non-zero.
#
# Usage: scripts/smoke.sh [REF] [TARGET] [--assistant claude|copilot-cli] [--capability rag|wiki|flow]
#   REF          git ref to install from (default: master, the real distribution channel)
#   TARGET       existing repo to run against; omitted → neutral synthetic fixture in a temp dir
#   --assistant  target assistant (default: claude)
#   --capability capability to smoke (default: rag)
set -euo pipefail

REF="master"
TARGET=""
ASSISTANT="claude"
CAPABILITY="rag"
# E15-FEAT-012: ref the host STARTS from. Empty = install-only (behaviour unchanged).
FROM_REF=""

# Parse: positional REF then TARGET (backward compatible with the pytest wrapper), plus flags.
_positional=()
while [ $# -gt 0 ]; do
    case "$1" in
        --assistant)  ASSISTANT="$2"; shift 2;;
        --capability) CAPABILITY="$2"; shift 2;;
        --from-ref)   FROM_REF="$2"; shift 2;;
        --assistant=*)  ASSISTANT="${1#*=}"; shift;;
        --capability=*) CAPABILITY="${1#*=}"; shift;;
        --from-ref=*)   FROM_REF="${1#*=}"; shift;;
        *) _positional+=("$1"); shift;;
    esac
done
[ "${#_positional[@]}" -ge 1 ] && REF="${_positional[0]}"
[ "${#_positional[@]}" -ge 2 ] && TARGET="${_positional[1]}"

REPO_URL="https://github.com/themetriost/Sertor"
SERTOR_SOURCE="git+${REPO_URL}@${REF}#subdirectory=packages/sertor"
FLOW_SOURCE="git+${REPO_URL}@${REF}#subdirectory=packages/sertor-flow"
IS_UPGRADE=0
[ -n "$FROM_REF" ] && IS_UPGRADE=1
FROM_SERTOR_SOURCE="git+${REPO_URL}@${FROM_REF}#subdirectory=packages/sertor"
FROM_FLOW_SOURCE="git+${REPO_URL}@${FROM_REF}#subdirectory=packages/sertor-flow"
IS_COPILOT=0
[ "$ASSISTANT" = "copilot-cli" ] && IS_COPILOT=1
UPGRADE_OUT=""   # the upgrade report, read by the no-stale-divergence outcome

fail() { echo "SMOKE_FAIL: $1" >&2; exit 1; }

# An environment impediment is NOT a product defect. Collapsing the two teaches people to ignore the
# gate — the dynamic that made v0.3.3 necessary. Distinct marker AND exit code (parity with .ps1).
fail_env() { echo "SMOKE_ENV: $1" >&2; exit 2; }

# Every asserted outcome goes through here, so a failure NAMES the outcome and the context (FR-008).
assert_outcome() {
    # $1 = outcome name, $2 = 0/1 ok flag, $3 = detail
    if [ "$2" -eq 1 ]; then
        echo "[upgrade] OK   $1"
        return 0
    fi
    fail "upgrade outcome '$1' diverged — $3 [assistant=$ASSISTANT capability=$CAPABILITY from=$FROM_REF to=$REF]"
}

case "$ASSISTANT" in claude|copilot-cli) ;; *) fail "invalid --assistant: $ASSISTANT";; esac
case "$CAPABILITY" in rag|wiki|flow) ;; *) fail "invalid --capability: $CAPABILITY";; esac

command -v uvx >/dev/null 2>&1 || fail "required tool not found in PATH: uvx"
command -v uv  >/dev/null 2>&1 || fail "required tool not found in PATH: uv"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Interpreter for the small shared helpers (planting). `python3` on every CI runner we use;
# `python` as the fallback for hosts where only that name exists.
PYTHON="$(command -v python3 || command -v python)"
REPO_CHECKOUT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Resolve the host: real target OR neutral synthetic fixture in system temp --------------------
CREATED_HOST=0
if [ -z "$TARGET" ]; then
    HOST="$(mktemp -d "${TMPDIR:-/tmp}/sertor-smoke-XXXXXX")"  # system temp = outside the checkout
    CREATED_HOST=1
else
    [ -d "$TARGET" ] || fail "target is not a directory: $TARGET"
    HOST="$(cd "$TARGET" && pwd)"
fi

# NB: must return 0. As an EXIT trap its final status becomes the script's exit code, so a
# short-circuited `&&` chain (e.g. when CREATED_HOST=0 for a --target run) would make a fully
# successful smoke exit 1. Use if/fi (returns 0 when the guard is false) + an explicit `return 0`.
cleanup() {
    if [ "$CREATED_HOST" -eq 1 ] && [ -n "${HOST:-}" ] && [ -d "$HOST" ]; then
        rm -rf "$HOST"
    fi
    return 0
}
trap cleanup EXIT

# Guard: never run inside the Sertor checkout (would let uv resolve sertor-core from the workspace).
case "$HOST/" in
    "$REPO_CHECKOUT"/*) fail "host '$HOST' is inside the Sertor checkout '$REPO_CHECKOUT' — isolation requires a host OUTSIDE the checkout";;
esac

echo "[smoke] assistant = $ASSISTANT | capability = $CAPABILITY"
echo "[smoke] host = $HOST"

# Scrub inherited SERTOR_* (and UV workspace discovery) so the developer dogfood env does not leak.
for v in $(env | grep -oE '^SERTOR_[A-Z0-9_]+' || true); do unset "$v"; done
# Also drop an inherited active venv (e.g. CI's `uv sync` exports VIRTUAL_ENV=<checkout>/.venv):
# `uv run --project .sertor` would warn it is ignored. Unset it so the smoke env stays clean.
unset VIRTUAL_ENV || true
export UV_NO_WORKSPACE=1

assert_path() { [ -e "$HOST/$1" ] || fail "expected artifact missing: $1"; }
assert_marker() {
    [ -f "$HOST/$1" ] || fail "instruction file missing: $1"
    grep -q -- "$2" "$HOST/$1" || fail "marker '$2' not found in $1"
}

new_synthetic_host() {
    cat > "$HOST/README.md" <<'EOF'
# Acme Widgets

A small sample project used to exercise the Sertor smoke test. It ships a documented helper function
and a TypeScript utility so the index has real code and documentation to retrieve.
EOF
    mkdir -p "$HOST/src"
    cat > "$HOST/src/app.py" <<'EOF'
def add(a: int, b: int) -> int:
    """Return the sum of two integers (sample function for the smoke test)."""
    return a + b


def greet(name: str) -> str:
    """Build a friendly greeting for the given name."""
    return f"Hello, {name}!"
EOF
    cat > "$HOST/src/utils.ts" <<'EOF'
// Format a label for display in the Acme Widgets UI.
export function formatLabel(text: string): string {
    return text.trim().toUpperCase();
}
EOF
}

# =================================================================================================
# Capability: RAG — install (assets) + runtime (index -> doctor -> search)
# =================================================================================================
rag_smoke() {
    echo "[smoke] installing rag capability ($ASSISTANT) ..."
    INSTALL_OUT="$(cd "$HOST" && uvx --refresh --from "$SERTOR_SOURCE" sertor install rag \
        --assistant "$ASSISTANT" --backend local --no-rerank --no-graph --corpus smoke \
        --target "$HOST" 2>&1)" || { echo "$INSTALL_OUT"; fail "install rag failed"; }
    echo "$INSTALL_OUT"

    SERTOR_DIR="$HOST/.sertor"
    [ -d "$SERTOR_DIR" ] || fail ".sertor/ not deposited"

    # Proof of isolation: the runtime lock must resolve sertor-core FROM GIT, never from the local
    # workspace path — otherwise the smoke would test the working tree, not the distribution.
    if [ -f "$SERTOR_DIR/uv.lock" ]; then
        if grep -A2 'name = "sertor-core"' "$SERTOR_DIR/uv.lock" | grep -q 'git = "https://github.com/themetriost/Sertor'; then
            echo "[smoke] isolation OK (sertor-core resolved from git in .sertor/uv.lock)"
        else
            fail "sertor-core is NOT resolved from git in .sertor/uv.lock (local-path leak — isolation broken)"
        fi
    else
        echo "[smoke] note: .sertor/uv.lock absent (--no-deps?); cannot prove git isolation"
    fi
    assert_path ".mcp.json"
    if [ "$IS_COPILOT" -eq 1 ]; then
        assert_path ".github/skills/guided-setup/SKILL.md"
        assert_path ".github/agents/concierge.agent.md"
    else
        assert_path ".claude/skills/guided-setup/SKILL.md"
        assert_path ".claude/agents/concierge.md"
    fi
    echo "[smoke] install OK (.sertor/, .mcp.json, UX assets present)"

    # Provider -> hash (zero-download, deterministic). The .env is loaded with override=True, so
    # editing the file is the robust way to force the provider for runtime commands.
    ENV_FILE="$SERTOR_DIR/.env"
    [ -f "$ENV_FILE" ] || fail ".sertor/.env not found after install"
    if grep -qE '^SERTOR_EMBED_PROVIDER=' "$ENV_FILE"; then
        sed -i.bak -E 's/^SERTOR_EMBED_PROVIDER=.*/SERTOR_EMBED_PROVIDER=hash/' "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    else
        printf '\nSERTOR_EMBED_PROVIDER=hash\n' >> "$ENV_FILE"
    fi
    echo "[smoke] provider forced to hash"

    cd "$HOST"

    # Index (the heart — catches the cwd/anchor bug) ----------------------------------------------
    echo "[smoke] indexing ..."
    INDEX_OUT="$(uv run --project .sertor sertor-rag index . 2>&1)" || { echo "$INDEX_OUT"; fail "index failed"; }
    echo "$INDEX_OUT"
    DOCUMENTS="$(printf '%s' "$INDEX_OUT" | grep -oE 'documents=[0-9]+' | head -n1 | cut -d= -f2)"
    [ -n "$DOCUMENTS" ] || fail "index output has no documents=N marker"
    [ "$DOCUMENTS" -gt 0 ] || fail "documents=$DOCUMENTS (expected > 0; cwd/anchor bug would give 0)"
    echo "[smoke] indexed documents=$DOCUMENTS"

    # Anchoring: index under .sertor/.index, NOT at host root -------------------------------------
    [ -d "$SERTOR_DIR/.index" ] || fail ".sertor/.index does not exist (index anchored wrong)"
    [ ! -d "$HOST/.index" ]     || fail "host-root .index exists (cwd/anchor regression)"
    echo "[smoke] anchoring OK (.sertor/.index present, root .index absent)"

    # Doctor -------------------------------------------------------------------------------------
    #    Capture stdout only: the provider emits a 'lexical-only' warning to stderr that would
    #    otherwise pollute the JSON (stderr flows to the terminal, shown but not parsed).
    echo "[smoke] running doctor ..."
    DOCTOR_OUT="$(uv run --project .sertor sertor-rag doctor --json)" || fail "doctor exited non-zero (a critical area failed)"
    OVERALL="$(printf '%s' "$DOCTOR_OUT" | python3 -c 'import sys,json; print(json.load(sys.stdin)["overall"])')"
    case "$OVERALL" in pass|warn) ;; *) fail "doctor overall=$OVERALL (expected pass|warn)";; esac
    for area in index config provider; do
        st="$(printf '%s' "$DOCTOR_OUT" | python3 -c "import sys,json; a={x['name']:x['status'] for x in json.load(sys.stdin)['areas']}; print(a.get('$area','MISSING'))")"
        [ "$st" = "pass" ] || fail "doctor $area area=$st (expected pass)"
    done
    echo "[smoke] doctor OK (overall=$OVERALL, index/config/provider=pass)"

    # Search -------------------------------------------------------------------------------------
    #    Capture stdout only (same stderr-warning reason as doctor).
    echo "[smoke] searching ..."
    SEARCH_OUT="$(uv run --project .sertor sertor-rag search "greeting function" --json)" || fail "search failed"
    RESULTS="$(printf '%s' "$SEARCH_OUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); n=(len(d.get("docs",[]))+len(d.get("code",[]))) if isinstance(d,dict) else len(d); print(n)')"
    [ "$RESULTS" -gt 0 ] || fail "search returned no results"
    echo "[smoke] search OK (results=$RESULTS)"
    # MCP server starts --------------------------------------------------------------------
    # The steps above pass with a DEAD MCP server: `doctor` reports the registration in
    # `.mcp.json` rather than the startup (E10-FEAT-072) and `search` goes through the CLI. So
    # before feature 128 no install smoke could see a host receiving zero tools — which is
    # precisely how that defect reached three nodes.
    echo "[smoke] importing the MCP server ..."
    if ! _mcp_import="$(uv run --project .sertor python -c "import sertor_mcp.server; print('ok')" 2>&1)"; then
        echo "$_mcp_import"
        fail "the MCP server cannot be imported: the host would receive NO tools while doctor stays green"
    fi
    echo "[smoke] MCP server import OK"

    echo ""
    echo "SMOKE_OK assistant=$ASSISTANT capability=rag doctor=$OVERALL documents=$DOCUMENTS results=$RESULTS"
}

# =================================================================================================
# Capability: WIKI — install (deposit-only, no runtime; no .sertor/, no sertor-core install)
# =================================================================================================
wiki_smoke() {
    echo "[smoke] installing wiki capability ($ASSISTANT) ..."
    INSTALL_OUT="$(cd "$HOST" && uvx --refresh --from "$SERTOR_SOURCE" sertor install wiki \
        --assistant "$ASSISTANT" --target "$HOST" 2>&1)" || { echo "$INSTALL_OUT"; fail "install wiki failed"; }
    echo "$INSTALL_OUT"

    assert_path "wiki/wiki.config.toml"
    assert_path "wiki/index.md"
    if [ "$IS_COPILOT" -eq 1 ]; then
        assert_path ".github/skills/wiki-author/SKILL.md"
        assert_path ".github/agents/wiki-curator.agent.md"
        assert_path ".github/hooks/wiki-pending-check.py"
        assert_path ".github/hooks/_hooklib.py"
        assert_path ".github/hooks/sertor-hooks.json"
        assert_marker ".github/copilot-instructions.md" "SERTOR:WIKI-RITUAL"
    else
        assert_path ".claude/skills/wiki-author/SKILL.md"
        assert_path ".claude/commands/wiki.md"
        assert_path ".claude/agents/wiki-curator.md"
        assert_path ".claude/hooks/wiki-pending-check.py"
        assert_path ".claude/hooks/_hooklib.py"
        assert_path ".claude/settings.json"
        assert_marker "CLAUDE.md" "SERTOR:WIKI-RITUAL"
    fi
    echo "[smoke] wiki deposit OK (skill, agent, hooks, config, scaffold, ritual block)"

    echo ""
    echo "SMOKE_OK assistant=$ASSISTANT capability=wiki deposit=ok"
}

# =================================================================================================
# Capability: FLOW (governance) — install (deposit-only; launches `specify init`, NETWORK)
# =================================================================================================
flow_smoke() {
    echo "[smoke] installing governance (flow) capability ($ASSISTANT) ..."
    INSTALL_OUT="$(cd "$HOST" && uvx --refresh --from "$FLOW_SOURCE" sertor-flow install \
        --assistant "$ASSISTANT" --target "$HOST" 2>&1)" || { echo "$INSTALL_OUT"; fail "sertor-flow install failed"; }
    echo "$INSTALL_OUT"

    assert_path ".specify/templates/plan-template.md"
    assert_path ".specify/memory/constitution.md"
    if [ "$IS_COPILOT" -eq 1 ]; then
        assert_path ".github/prompts/speckit.specify.prompt.md"
        assert_path ".github/agents/requirements-analyst.agent.md"
        assert_path ".github/agents/configuration-manager.agent.md"
        assert_path ".github/agents/requirements.agent.md"
        assert_marker ".github/copilot-instructions.md" "SERTOR:SDLC-RITUAL"
    else
        assert_path ".claude/skills/speckit-specify/SKILL.md"
        assert_path ".claude/agents/requirements-analyst.md"
        assert_path ".claude/agents/configuration-manager.md"
        assert_path ".claude/skills/requirements/SKILL.md"
        assert_marker "CLAUDE.md" "SERTOR:SDLC-RITUAL"
    fi
    echo "[smoke] governance deposit OK (speckit, constitution, authored surfaces, SDLC block)"

    echo ""
    echo "SMOKE_OK assistant=$ASSISTANT capability=flow deposit=ok"
}

# =================================================================================================
# E15-FEAT-012 — upgrade flow: install the PREVIOUS release, upgrade, assert outcomes on the HOST
# =================================================================================================

# THE outcome list (FR-015). Every entry exists because a defect really happened: adding one after a
# new field report must be one more line here, never a restructuring — otherwise the list ages and
# the guard only protects the past. Kept in parity with `Assert-UpgradeOutcomes` in smoke.ps1.
assert_upgrade_outcomes() {
    _cap="$1"
    _sertor_dir="$HOST/.sertor"

    # 1. The pin moved. Defect: the recorded source stayed at the old version after `upgrade` —
    #    reported by THREE independent nodes, and the reason v0.3.1 existed.
    if [ -f "$_sertor_dir/pyproject.toml" ]; then
        if grep -qF "$FROM_REF" "$_sertor_dir/pyproject.toml"; then
            assert_outcome "pin-moved" 0 "the runtime source still references '$FROM_REF' in .sertor/pyproject.toml"
        else
            assert_outcome "pin-moved" 1 ""
        fi
    else
        echo "[upgrade] n/a  pin-moved (capability '$_cap' creates no runtime)"
    fi

    # 2. Exactly ONE session automation, and it is the current one. Defect: identity by command string
    #    made a re-wire look new, so the hook was duplicated (E10-FEAT-032) with the broken copy live.
    if [ "$IS_COPILOT" -eq 1 ]; then
        _settings_rel=".github/hooks/sertor-hooks.json"
    else
        _settings_rel=".claude/settings.json"
    fi
    if [ -f "$HOST/$_settings_rel" ]; then
        for _stem in rag-freshness wiki-guard memory-capture; do
            # `|| _count=0`: under `set -euo pipefail` a `grep` that finds NOTHING exits 1, the
            # pipeline fails, and the script would die HERE — silently, with no SMOKE_FAIL line. An
            # absent stem is normal (a rag host has no wiki hooks), so it must read as zero, not as a
            # crash. Observed on the first real run: the gate died opaquely on `wiki-guard`, which is
            # exactly the failure shape `assert_outcome` exists to prevent.
            _count="$(grep -oF "$_stem" "$HOST/$_settings_rel" | wc -l | tr -d ' ')" || _count=0
            if [ "$_count" -gt 0 ]; then
                if [ "$_count" -le 2 ]; then
                    assert_outcome "hook-single:$_stem" 1 ""
                else
                    assert_outcome "hook-single:$_stem" 0 "hook '$_stem' appears $_count times in $_settings_rel (duplicated wiring)"
                fi
            fi
        done
    fi

    # 3. Host-owned configuration preserved. Defect: fixing E2-FEAT-022 nearly zeroed the corpus on
    #    every upgrade — caught by a MANUAL run, not by the tests.
    if [ -f "$_sertor_dir/.env" ]; then
        if grep -qE "SERTOR_CORPUS[[:space:]]*=[[:space:]]*smoke" "$_sertor_dir/.env"; then
            assert_outcome "host-config-preserved" 1 ""
        else
            assert_outcome "host-config-preserved" 0 "SERTOR_CORPUS=smoke is gone from .sertor/.env after the upgrade"
        fi
    fi

    # 4. The recorded invocation has the current shape. Defect: `--directory` kept because it "was
    #    already there" — the RAG resolved the index in the wrong folder for a month.
    if [ -f "$HOST/.mcp.json" ]; then
        if grep -qF -- "--directory" "$HOST/.mcp.json"; then
            assert_outcome "mcp-invocation-shape" 0 "the MCP registration still uses --directory instead of --project"
        else
            assert_outcome "mcp-invocation-shape" 1 ""
        fi
    fi

    # 5. Nothing was left stale. Defect: `install` is non-destructive and leaves a divergent file in
    #    place (PRESENT_DIVERGENT) — correct for install, WRONG for upgrade, whose contract is to
    #    replace our own artefacts. It blocked hook fixes that had already been released. The signal
    #    is in the upgrade's own report, so reading it costs nothing.
    if printf '%s' "$UPGRADE_OUT" | grep -qF "PRESENT_DIVERGENT"; then
        assert_outcome "no-stale-divergence" 0 "the upgrade left an artefact divergent instead of replacing it"
    else
        assert_outcome "no-stale-divergence" 1 ""
    fi

    # 6. The version the host reports as INSTALLED is DERIVED from the runtime, not read from the
    #    install-time stamp. Defect E2-FEAT-021 — already FIXED, which is precisely why the assertion
    #    is worth its lines: being fixed and ARRIVING at a host that upgrades are different facts, and
    #    only the second is what the host experiences. The stamp records the version of the *installer
    #    that ran*; a host whose runtime was current but whose stamp lagged reported a permanent false
    #    `behind`, with a suggested remedy that was not even executable there.
    #
    #    Discriminating BY CONSTRUCTION, not by luck: we plant a stamp that LAGS the runtime — the
    #    field condition itself. Reading the stamp yields `behind`; deriving from the lock yields
    #    up-to-date. Without the planted stamp the two sources agree on this fixture and the assertion
    #    would pass while measuring nothing. `latest` is seeded into the cache so the check stays
    #    offline: the network is not what is under test here.
    _vc_hook="$HOST/.claude/hooks/version-check.py"
    [ "$IS_COPILOT" -eq 1 ] && _vc_hook="$HOST/.github/hooks/version-check.py"
    if [ -d "$_sertor_dir" ] && [ -f "$_vc_hook" ]; then
        _runtime_ver=""
        if [ -f "$_sertor_dir/uv.lock" ]; then
            _runtime_ver="$(awk -F'"' '/^name = "sertor-core"$/{f=1} f && /^version = /{print $2; exit}' \
                "$_sertor_dir/uv.lock")"
        fi
        # fail, not skip: an unreadable lock on a host that just upgraded is the very state this
        # outcome exists to observe. A silent skip here would be the gate disabling itself.
        [ -n "$_runtime_ver" ] || fail "version-derived: no sertor-core version in .sertor/uv.lock"

        printf '0.0.1\n' > "$_sertor_dir/.sertor-version"
        cat > "$_sertor_dir/.version-check.json" <<EOF
{
  "schema": "version.check/1",
  "verdict": "unknown",
  "installed": "",
  "latest": "$_runtime_ver",
  "checked_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
        # CLAUDE_PROJECT_DIR is pinned to the throwaway host ON PURPOSE: the hook honours it over the
        # event's cwd, so a run started from inside a real session would otherwise write its state
        # into THAT project instead of the fixture.
        _vc_out="$(printf '{}' | CLAUDE_PROJECT_DIR="$HOST" uv run --no-project python "$_vc_hook" 2>&1)" || true
        if [ -n "$_vc_out" ]; then echo "$_vc_out"; fi

        _vc_state="$(cat "$_sertor_dir/.version-check.json")"
        if printf '%s' "$_vc_state" | grep -qF '"installed_source": "runtime-lock"' \
           && ! printf '%s' "$_vc_state" | grep -qF '"verdict": "behind"'; then
            assert_outcome "version-derived-from-runtime" 1 ""
        else
            assert_outcome "version-derived-from-runtime" 0 \
                "the host derived the installed version from the planted stale stamp instead of the lock (runtime sertor-core $_runtime_ver); state: $(printf '%s' "$_vc_state" | tr '\n' ' ')"
        fi
    else
        echo "[upgrade] n/a  version-derived-from-runtime (capability '$_cap' deposits no version-check hook)"
    fi

    # 7. The MCP server IMPORTS. Defect E10-FEAT-070: on a host whose lock froze the SDK's new major
    #    the server died at import and the assistant received NO tools — while `doctor` stayed green,
    #    because its `mcp` check reads the registration in `.mcp.json`, not the startup. So this cannot
    #    be folded into `health-green`: the green is precisely what failed to see it.
    #    ⚠️ THE OUTCOME IS ASSERTED ON EVERY JUMP, and the planting decides WHICH CLAIM it supports —
    #    not whether it runs. It used to print `n/a` when the starting release was unaffected, and that
    #    made it EXPIRE: from `v0.4.2` on, the previous release carries the ceiling, so the condition is
    #    unplantable BY CONSTRUCTION and the outcome went permanently `n/a` — which the wrapper reads as
    #    a missing name, painting `master` red on every push (measured 2026-09-16, first push after the
    #    tag). The two claims were conflated: "an affected host was HEALED" is historical and expires the
    #    moment the fix ships; "after the upgrade the server STARTS" is permanent and still catches a
    #    regression. We assert the permanent one always and annotate which of the two was observed.
    #    A repair makes its own defect irreproducible: a guard whose premise is the unrepaired state
    #    dies of its own success.
    #    ⚠️ WHAT THIS OUTCOME DOES AND DOES NOT DISCRIMINATE. It asserts that an affected host ends
    #    the upgrade with a server that starts — which is what the host cares about — but two
    #    different mechanisms can satisfy it: the CEILING pulling the SDK back to the old line, or
    #    the CODE now running on the new one. On the current jump the credit goes to the ceiling
    #    (measured 2026-09-13). What measures the porting itself is the CI step that runs the MCP
    #    tests against the other SDK line; the two presidia cover different things and neither
    #    replaces the other.
    if [ -d "$_sertor_dir" ] && [ "$_cap" = "rag" ]; then
        if _imp_out="$(cd "$HOST" && uv run --project .sertor python -c "import sertor_mcp.server; print('ok')" 2>&1)"; then
            _imp_ok=1
        else
            _imp_ok=0
        fi
        # The outcome is ASSERTED EITHER WAY; only the CLAIM it supports changes with the planting.
        # The diagnosis on failure differs, so it is chosen before asserting, not after.
        if [ "${PLANTED_BROKEN:-0}" -eq 1 ]; then
            _imp_why="the MCP server still cannot be imported AFTER the upgrade, so the host keeps receiving no tools: $_imp_out"
        else
            _imp_why="the MCP server cannot be imported after the upgrade, and it was NOT broken before: this jump BREAKS it: $_imp_out"
        fi
        assert_outcome "mcp-server-imports" "$_imp_ok" "$_imp_why"
        if [ "${PLANTED_BROKEN:-0}" -eq 1 ]; then
            echo "[upgrade]      ^ planted: an AFFECTED host ended the upgrade with a server that STARTS (a repair was observed)"
        else
            echo "[upgrade]      ^ not plantable: '$FROM_REF' already carries the ceiling — this asserts NO REGRESSION, not a repair"
        fi
    fi

    # 8. Health is green — the catch-all for what the seven above do not name.
    if [ -d "$_sertor_dir" ]; then
        if _doctor_out="$(uv run --project "$_sertor_dir" sertor-rag doctor 2>&1)"; then
            assert_outcome "health-green" 1 ""
        else
            assert_outcome "health-green" 0 "doctor failed after the upgrade: $_doctor_out"
        fi
    fi
}

upgrade_flow() {
    _cap="$1"
    if [ "$_cap" = "flow" ]; then
        _from_src="$FROM_FLOW_SOURCE"; _to_src="$FLOW_SOURCE"; _exe="sertor-flow"
    else
        _from_src="$FROM_SERTOR_SOURCE"; _to_src="$SERTOR_SOURCE"; _exe="sertor"
    fi

    echo "[upgrade] installing PREVIOUS release $FROM_REF ($_cap / $ASSISTANT) ..."
    if [ "$_cap" = "rag" ]; then
        _out="$(cd "$HOST" && uvx --refresh --from "$_from_src" "$_exe" install "$_cap" \
            --assistant "$ASSISTANT" --backend local --no-rerank --no-graph --corpus smoke \
            --target "$HOST" 2>&1)" || { echo "$_out"; fail_env "install of previous release '$FROM_REF' failed (ref reachable? network?)"; }
    else
        _out="$(cd "$HOST" && uvx --refresh --from "$_from_src" "$_exe" install "$_cap" \
            --assistant "$ASSISTANT" --target "$HOST" 2>&1)" || { echo "$_out"; fail_env "install of previous release '$FROM_REF' failed (ref reachable? network?)"; }
    fi
    echo "$_out"

    # Same fixture policy the install flow already applies: the install writes
    # SERTOR_EMBED_PROVIDER=glove, whose vectors are a ~822 MB download the runner must not make. It
    # is a FIXTURE choice, not a product one — and the product question it could hide was checked:
    # `host-config-preserved` passes, so the upgrade preserves .env; the provider stays `glove`
    # because that is the install default, not because the upgrade touched it.
    _env_file="$HOST/.sertor/.env"
    if [ -f "$_env_file" ]; then
        if grep -qE '^SERTOR_EMBED_PROVIDER=' "$_env_file"; then
            sed -i.bak -E 's/^SERTOR_EMBED_PROVIDER=.*/SERTOR_EMBED_PROVIDER=hash/' "$_env_file" && rm -f "$_env_file.bak"
        else
            printf '\nSERTOR_EMBED_PROVIDER=hash\n' >> "$_env_file"
        fi
        echo "[upgrade] provider forced to hash (fixture: no 822 MB download on the runner)"
    fi

    # A host that upgrades HAS an index, and it was built by the OLD version. Skipping this step is
    # what made the first run report `health-green` as diverged: `doctor` said `index_absent`, which
    # was true of the fixture and of no real host. It is not only fixture, though — indexing HERE,
    # with the previous release, is what turns `health-green` into a question the install-only smoke
    # cannot ask at all: does the new version still READ the index the previous one wrote? A manifest
    # that stopped being readable would otherwise cost the host its index in silence.
    if [ "$_cap" = "rag" ] && [ -d "$HOST/.sertor" ]; then
        echo "[upgrade] indexing with the PREVIOUS release ..."
        # fail_env, not fail: a previous release that cannot index is a starting line we never
        # reached — it says nothing about $REF, which is the thing under test.
        _idx_out="$(cd "$HOST" && uv run --project .sertor sertor-rag index . 2>&1)" \
            || { echo "$_idx_out"; fail_env "index with the previous release '$FROM_REF' failed"; }
        printf '%s\n' "$_idx_out" | tail -n 2
    fi

    # PLANT THE CONDITION of an already-affected host (E10-FEAT-070, feature 128). The MCP SDK's
    # major 2.0.0 removed the submodule older Sertor versions import, so every host that re-resolved
    # after 2026-07-28 ended up with a server that dies at import — three nodes measured it, two ran
    # without MCP for over a month. A freshly created fixture resolves a working version, so
    # `mcp-server-imports` after the upgrade would pass GRATIS: it would measure nothing. We force the
    # OLD runtime onto the new major, and ASSERT IT IS BROKEN FIRST — that assertion is what turns the
    # outcome into a measure (the same trade as the planted stale stamp in #6).
    PLANTED_BROKEN=0
    if [ "$_cap" = "rag" ] && [ -d "$HOST/.sertor" ]; then
        # HOW the condition is planted, and why it takes two edits. The installer writes the runtime
        # source as a BARE git reference, so the runtime follows the default branch — NOT the release
        # the installer came from (measured 2026-09-13: uv resolved `sertor-core==0.4.1` carrying the
        # CEILING, which exists only on the default branch). With the ceiling in force `mcp>=2` cannot
        # be resolved at all, so we also pin the runtime to `$FROM_REF` — the release the host is
        # supposed to be starting FROM. That pin is what makes the fixture match the field: a host
        # whose lock froze the new major because its Sertor had no ceiling yet. `upgrade` moves the pin
        # back (outcome #1), so nothing planted here survives except the frozen SDK major.
        PLANT_SKIPPED=0
        # The planting itself lives in `scripts/smoke_plant_mcp.py`, shared with `smoke.ps1` so the
        # two scripts cannot drift on it: it adds the frozen SDK major AND pins `sertor-core` to the
        # starting release (without that pin the runtime follows the default branch, which already
        # carries the ceiling, and the condition is simply unsatisfiable).
        "$PYTHON" "$SCRIPT_DIR/smoke_plant_mcp.py" "$HOST/.sertor/pyproject.toml" "$FROM_REF"
        # the SDK is re-resolved on purpose: `uv sync` alone is conservative and keeps the locked 1.x, so 
        # nothing would be planted. `--upgrade-package mcp` is the mechanism that hit the field — node Noetix was 
        # broken by the third command of OUR upgrade procedure, `uv sync --upgrade`, which re-resolved its saf
        # e 1.x into the new major two days after that major shipped.
        if ! _plant_out="$(cd "$HOST" && uv sync --project .sertor --upgrade-package mcp 2>&1)"; then
            # Two very different reasons land here, and collapsing them would hide the one that
            # matters. If the STARTING release already carries the ceiling, `mcp>=2` is simply
            # unsatisfiable: that release is not affected, so there is nothing to repair on this jump.
            # Anything else is an impediment.
            case "$_plant_out" in
                *unsatisfiable*|*"No solution found"*)
                    echo "[upgrade] note: '$FROM_REF' already carries the mcp ceiling — the condition does not exist on this jump"
                    PLANT_SKIPPED=1
                    ;;
                *)
                    echo "$_plant_out"
                    # fail_env: an impediment says nothing about $REF, which is under test.
                    fail_env "could not plant the mcp>=2 condition (uv sync failed)"
                    ;;
            esac
        fi
        if [ "$PLANT_SKIPPED" -eq 1 ]; then
            :
        elif (cd "$HOST" && uv run --project .sertor python -c "import sertor_mcp.server" >/dev/null 2>&1); then
            # Not a failure of $REF: the previous release already survives the new major, so this jump
            # cannot demonstrate the repair. Say so, instead of reporting a green that measured a
            # condition which was never there.
            echo "[upgrade] note: the PREVIOUS release imports fine on mcp>=2 — nothing to repair on this jump"
        else
            PLANTED_BROKEN=1
            echo "[upgrade] planted: the PREVIOUS release cannot import its MCP server (as in the field)"
        fi
    fi

    echo "[upgrade] upgrading $FROM_REF -> $REF ..."
    UPGRADE_OUT="$(cd "$HOST" && uvx --refresh --from "$_to_src" "$_exe" upgrade "$_cap" \
        --assistant "$ASSISTANT" --target "$HOST" 2>&1)" || { echo "$UPGRADE_OUT"; fail "upgrade $_cap failed"; }
    echo "$UPGRADE_OUT"

    # Exit code 0 is NOT an outcome: `upgrade` used to succeed while moving nothing (SC-004).
    assert_upgrade_outcomes "$_cap"

    echo ""
    echo "SMOKE_OK assistant=$ASSISTANT capability=$_cap upgrade=$FROM_REF->$REF"
}

# 1. Synthetic host (when no TARGET) --------------------------------------------------------------
if [ "$CREATED_HOST" -eq 1 ]; then
    new_synthetic_host
fi

# 2. Dispatch: upgrade flow when a starting ref was given, otherwise the install-only flow ---------
if [ "$IS_UPGRADE" -eq 1 ]; then
    upgrade_flow "$CAPABILITY"
    exit 0
fi

case "$CAPABILITY" in
    rag)  rag_smoke;;
    wiki) wiki_smoke;;
    flow) flow_smoke;;
esac

exit 0   # explicit success (the EXIT trap's cleanup returns 0, see above)
