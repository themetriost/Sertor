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

# Parse: positional REF then TARGET (backward compatible with the pytest wrapper), plus flags.
_positional=()
while [ $# -gt 0 ]; do
    case "$1" in
        --assistant)  ASSISTANT="$2"; shift 2;;
        --capability) CAPABILITY="$2"; shift 2;;
        --assistant=*)  ASSISTANT="${1#*=}"; shift;;
        --capability=*) CAPABILITY="${1#*=}"; shift;;
        *) _positional+=("$1"); shift;;
    esac
done
[ "${#_positional[@]}" -ge 1 ] && REF="${_positional[0]}"
[ "${#_positional[@]}" -ge 2 ] && TARGET="${_positional[1]}"

REPO_URL="https://github.com/themetriost/Sertor"
SERTOR_SOURCE="git+${REPO_URL}@${REF}#subdirectory=packages/sertor"
FLOW_SOURCE="git+${REPO_URL}@${REF}#subdirectory=packages/sertor-flow"
IS_COPILOT=0
[ "$ASSISTANT" = "copilot-cli" ] && IS_COPILOT=1

fail() { echo "SMOKE_FAIL: $1" >&2; exit 1; }

case "$ASSISTANT" in claude|copilot-cli) ;; *) fail "invalid --assistant: $ASSISTANT";; esac
case "$CAPABILITY" in rag|wiki|flow) ;; *) fail "invalid --capability: $CAPABILITY";; esac

command -v uvx >/dev/null 2>&1 || fail "required tool not found in PATH: uvx"
command -v uv  >/dev/null 2>&1 || fail "required tool not found in PATH: uv"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
        assert_path ".github/hooks/wiki-pending-check.ps1"
        assert_path ".github/hooks/sertor-hooks.json"
        assert_marker ".github/copilot-instructions.md" "SERTOR:WIKI-RITUAL"
    else
        assert_path ".claude/skills/wiki-author/SKILL.md"
        assert_path ".claude/commands/wiki.md"
        assert_path ".claude/agents/wiki-curator.md"
        assert_path ".claude/hooks/wiki-pending-check.ps1"
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

# 1. Synthetic host (when no TARGET) --------------------------------------------------------------
if [ "$CREATED_HOST" -eq 1 ]; then
    new_synthetic_host
fi

# 2. Dispatch to the requested capability ---------------------------------------------------------
case "$CAPABILITY" in
    rag)  rag_smoke;;
    wiki) wiki_smoke;;
    flow) flow_smoke;;
esac

exit 0   # explicit success (the EXIT trap's cleanup returns 0, see above)
