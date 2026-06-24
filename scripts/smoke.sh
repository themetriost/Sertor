#!/usr/bin/env bash
# End-to-end smoke test of the Sertor RAG capability against the real distribution (git+url@master).
#
# Installs the RAG capability into a host directory exactly as a third-party project would
# (`uvx --from git+url#subdirectory=packages/sertor sertor install rag ...`), then exercises the
# runtime CLI end-to-end: index -> doctor -> search. It catches integration bugs the offline suite
# cannot (CLI discoverability, cwd/index anchoring), because it drives the real installed
# entry-points from a clean host.
#
# ISOLATION (no "Sertor on Sertor"): the smoke runs in a host directory OUTSIDE the Sertor checkout,
# with an environment scrubbed of inherited SERTOR_* variables, and launches `uvx` with
# cwd = the host dir plus UV_NO_WORKSPACE=1 so `uv` cannot discover the local workspace. This
# guarantees `sertor-core` is BUILT FROM GIT (look for `Building sertor-core @ git+...` in the
# install log), never resolved from the local path.
#
# FIXTURE vs REAL TARGET: by DEFAULT (no $2) the smoke creates a NEUTRAL synthetic project
# (README.md + src/app.py + src/utils.ts — a generic project, never Sertor files) in a temp dir and
# cleans it up. With a TARGET ($2) the smoke runs on THAT existing repo (and does NOT delete it). In
# CI the pytest wrapper (tests/integration/test_host_smoke.py) reads SERTOR_SMOKE_TARGET and forwards
# it — the dedicated CI target is the real C#/.NET repo `themetriost/PgnToFen`, cloned shallow.
#
# Provider = `hash` (zero-credentials, zero-download, deterministic). The install writes
# SERTOR_EMBED_PROVIDER=glove into .sertor/.env (would download ~822 MB), so the script rewrites
# that line to `hash` before any runtime command. `--no-rerank --no-graph` keep the venv slim.
#
# On success prints a single machine-checkable marker and exits 0:
#     SMOKE_OK doctor=<pass|warn> documents=<N> results=<M>
# On any failed assertion prints `SMOKE_FAIL: <reason>` and exits non-zero.
#
# Usage: scripts/smoke.sh [REF] [TARGET]
#   REF    git ref to install from (default: master, the real distribution channel)
#   TARGET existing repo to run against; omitted → neutral synthetic fixture in a temp dir
set -euo pipefail

REF="${1:-master}"
TARGET="${2:-}"
REPO_URL="https://github.com/themetriost/Sertor"
SOURCE="git+${REPO_URL}@${REF}#subdirectory=packages/sertor"

fail() { echo "SMOKE_FAIL: $1" >&2; exit 1; }

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

cleanup() { [ "$CREATED_HOST" -eq 1 ] && [ -n "${HOST:-}" ] && [ -d "$HOST" ] && rm -rf "$HOST"; }
trap cleanup EXIT

# Guard: never run inside the Sertor checkout (would let uv resolve sertor-core from the workspace).
case "$HOST/" in
    "$REPO_CHECKOUT"/*) fail "host '$HOST' is inside the Sertor checkout '$REPO_CHECKOUT' — isolation requires a host OUTSIDE the checkout";;
esac

echo "[smoke] host = $HOST"
echo "[smoke] source = $SOURCE"

# Scrub inherited SERTOR_* (and UV workspace discovery) so the developer dogfood env does not leak.
for v in $(env | grep -oE '^SERTOR_[A-Z0-9_]+' || true); do unset "$v"; done
export UV_NO_WORKSPACE=1

# 1. Neutral synthetic project (generic — never Sertor files) -------------------------------------
if [ "$CREATED_HOST" -eq 1 ]; then
    cat > "$HOST/README.md" <<'EOF'
# Acme Widgets

A small sample project used to exercise the RAG smoke test. It ships a documented helper function
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
fi

# 2. Install the RAG capability from git+url (the real distribution path) --------------------------
#    cwd = host dir (outside the checkout) so uv never resolves sertor-core from the workspace.
echo "[smoke] installing rag capability ..."
INSTALL_OUT="$(cd "$HOST" && uvx --refresh --from "$SOURCE" sertor install rag --backend local \
    --no-rerank --no-graph --corpus smoke --target "$HOST" 2>&1)" || { echo "$INSTALL_OUT"; fail "install rag failed"; }
echo "$INSTALL_OUT"

SERTOR_DIR="$HOST/.sertor"
[ -d "$SERTOR_DIR" ]                                             || fail ".sertor/ not deposited"

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
[ -f "$HOST/.mcp.json" ]                                         || fail ".mcp.json not deposited"
[ -f "$HOST/.claude/skills/guided-setup/SKILL.md" ]             || fail "guided-setup SKILL.md not deposited"
[ -f "$HOST/.claude/agents/concierge.md" ]                      || fail "concierge.md not deposited"
echo "[smoke] install OK (.sertor/, .mcp.json, UX assets present)"

# 3. Provider -> hash (zero-download, deterministic). The .env is loaded with override=True, so
#    editing the file is the robust way to force the provider for runtime commands.
ENV_FILE="$SERTOR_DIR/.env"
[ -f "$ENV_FILE" ] || fail ".sertor/.env not found after install"
if grep -qE '^SERTOR_EMBED_PROVIDER=' "$ENV_FILE"; then
    sed -i.bak -E 's/^SERTOR_EMBED_PROVIDER=.*/SERTOR_EMBED_PROVIDER=hash/' "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
    printf '\nSERTOR_EMBED_PROVIDER=hash\n' >> "$ENV_FILE"
fi
echo "[smoke] provider forced to hash"

cd "$HOST"

# 4. Index (the heart — catches the cwd/anchor bug) -----------------------------------------------
echo "[smoke] indexing ..."
INDEX_OUT="$(uv run --project .sertor sertor-rag index . 2>&1)" || { echo "$INDEX_OUT"; fail "index failed"; }
echo "$INDEX_OUT"
DOCUMENTS="$(printf '%s' "$INDEX_OUT" | grep -oE 'documents=[0-9]+' | head -n1 | cut -d= -f2)"
[ -n "$DOCUMENTS" ] || fail "index output has no documents=N marker"
[ "$DOCUMENTS" -gt 0 ] || fail "documents=$DOCUMENTS (expected > 0; cwd/anchor bug would give 0)"
echo "[smoke] indexed documents=$DOCUMENTS"

# 5. Anchoring: index under .sertor/.index, NOT at host root --------------------------------------
[ -d "$SERTOR_DIR/.index" ] || fail ".sertor/.index does not exist (index anchored wrong)"
[ ! -d "$HOST/.index" ]     || fail "host-root .index exists (cwd/anchor regression)"
echo "[smoke] anchoring OK (.sertor/.index present, root .index absent)"

# 6. Doctor ---------------------------------------------------------------------------------------
#    Capture stdout only: the provider emits a 'lexical-only' warning to stderr that would otherwise
#    pollute the JSON (stderr flows to the terminal, shown to the operator but not parsed).
echo "[smoke] running doctor ..."
DOCTOR_OUT="$(uv run --project .sertor sertor-rag doctor --json)" || fail "doctor exited non-zero (a critical area failed)"
OVERALL="$(printf '%s' "$DOCTOR_OUT" | python3 -c 'import sys,json; print(json.load(sys.stdin)["overall"])')"
case "$OVERALL" in pass|warn) ;; *) fail "doctor overall=$OVERALL (expected pass|warn)";; esac
for area in index config provider; do
    st="$(printf '%s' "$DOCTOR_OUT" | python3 -c "import sys,json; a={x['name']:x['status'] for x in json.load(sys.stdin)['areas']}; print(a.get('$area','MISSING'))")"
    [ "$st" = "pass" ] || fail "doctor $area area=$st (expected pass)"
done
echo "[smoke] doctor OK (overall=$OVERALL, index/config/provider=pass)"

# 7. Search ---------------------------------------------------------------------------------------
#    Capture stdout only (same stderr-warning reason as doctor).
echo "[smoke] searching ..."
SEARCH_OUT="$(uv run --project .sertor sertor-rag search "greeting function" --json)" || fail "search failed"
RESULTS="$(printf '%s' "$SEARCH_OUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); n=(len(d.get("docs",[]))+len(d.get("code",[]))) if isinstance(d,dict) else len(d); print(n)')"
[ "$RESULTS" -gt 0 ] || fail "search returned no results"
echo "[smoke] search OK (results=$RESULTS)"

echo ""
echo "SMOKE_OK doctor=$OVERALL documents=$DOCUMENTS results=$RESULTS"
