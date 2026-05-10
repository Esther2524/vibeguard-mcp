#!/usr/bin/env bash
# scripts/see_it.sh
#
# The "see it work" walkthrough — runs the full VibeGuard flow on a
# clean copy of the shopify-store demo target and shows BEFORE / AFTER
# of everything it touches.
#
# Usage:  ./scripts/see_it.sh
#
# Override demo target: DEMO_TARGET=/path/to/your/repo ./scripts/see_it.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_TARGET="${DEMO_TARGET:-/tmp/shopify-store-demo}"
PY="$REPO_ROOT/.venv/bin/python"
KB_FILE="$HOME/.vibeguard/kb.json"
WORKSPACES_DIR="$HOME/vibeguard-workspaces"

bold()    { printf '\033[1m%s\033[0m\n' "$*"; }
dim()     { printf '\033[2m%s\033[0m\n' "$*"; }
red()     { printf '\033[31m%s\033[0m' "$*"; }
green()   { printf '\033[32m%s\033[0m' "$*"; }
cyan()    { printf '\033[36m%s\033[0m' "$*"; }
yellow()  { printf '\033[33m%s\033[0m' "$*"; }
hr()      { printf '\033[2m────────────────────────────────────────────────────────────────\033[0m\n'; }
section() { echo; printf '\033[1;36m▌ %s\033[0m\n' "$*"; hr; }

# ── prep ──
if [[ ! -x "$PY" ]]; then
  echo "❌ no venv. run: cd $REPO_ROOT && python3 -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi
if [[ ! -d "$DEMO_TARGET/.git" ]]; then
  echo "Cloning shopify-store demo target..."
  git clone --depth 1 https://github.com/ycecilia/shopify-store.git "$DEMO_TARGET" 2>&1 | tail -1
fi

# Reset everything
rm -f "$KB_FILE"
[[ -d "$WORKSPACES_DIR" ]] && rm -rf "$WORKSPACES_DIR"/*
(cd "$DEMO_TARGET" && git stash --include-untracked --quiet 2>/dev/null || true; git stash drop 2>/dev/null || true; git reset --hard HEAD --quiet; git clean -fd --quiet; rm -f vibeguard-owner-memory.md)

clear
bold "🛡️  VibeGuard — see it work"
echo
echo "  Demo target: $(cyan "$DEMO_TARGET")  (a vibe-coded shopify storefront)"
echo "  We're going to:"
echo "    1. Show you the BEFORE state (real secrets sitting in source code)"
echo "    2. Run the full VibeGuard flow"
echo "    3. Show you the AFTER state (secrets gone from source, contractor workspace ready)"
echo
read -r -p "Press Enter to start..."

# ════════════════ BEFORE ════════════════
section "BEFORE · what the owner has today"
echo
echo "$(yellow "▸ src/lib/config.ts")  $(dim "(the giant secrets dump)")"
hr
sed -n '1,12p' "$DEMO_TARGET/src/lib/config.ts" | sed 's/^/  /'
echo "  ..."
echo "  $(dim "(continues for 30+ lines with AWS keys, Google service account, admin password)")"
echo
echo "$(yellow "▸ src/lib/stripe_stuff.ts")  $(dim "(duplicated keys + leaky console.log)")"
hr
sed -n '1,17p' "$DEMO_TARGET/src/lib/stripe_stuff.ts" | sed 's/^/  /'
echo
echo "$(yellow "▸ files at the root")"
hr
ls -la "$DEMO_TARGET" | grep -E "^\.|\.env|config" | sed 's/^/  /' || true
ls "$DEMO_TARGET" | grep -E "^\.env" 2>/dev/null | sed 's/^/  /' || echo "  $(red "no .env file") $(dim "— secrets are hardcoded in src/lib/config.ts")"
echo

read -r -p "Press Enter to run VibeGuard..."

# ════════════════ RUN ════════════════
section "RUNNING · the three-tool flow"
echo
"$PY" "$REPO_ROOT/scripts/dry_run.py" "$DEMO_TARGET" 2>&1 | grep -E "PHASE|·|advisories:|secrets|preview|executed|workspace|applied|files in|owner memory|contractor brief|✓|✗|═|⚠️|📦|📝" | sed 's/^/  /'
echo

read -r -p "Press Enter to see what changed..."

# ════════════════ AFTER ════════════════
section "AFTER · owner's real codebase has been refactored"
echo
echo "$(green "▸ src/lib/config.ts")  $(dim "(now uses env vars — secrets gone from source)")"
hr
cat "$DEMO_TARGET/src/lib/config.ts" | sed 's/^/  /'
echo
echo "$(green "▸ NEW: .env.example")  $(dim "(template for the secrets that used to be hardcoded)")"
hr
cat "$DEMO_TARGET/.env.example" | sed 's/^/  /'
echo
echo "$(green "▸ NEW: .gitignore got an entry")  $(dim "(.env.local now properly ignored)")"
hr
tail -3 "$DEMO_TARGET/.gitignore" | sed 's/^/  /'
echo
echo "$(green "▸ NEW: vibeguard-owner-memory.md")  $(dim "(persistent context for owner's future sessions)")"
hr
cat "$DEMO_TARGET/vibeguard-owner-memory.md" | sed 's/^/  /'
echo

read -r -p "Press Enter to see Sarah's (the contractor's) workspace..."

# ════════════════ CONTRACTOR WORKSPACE ════════════════
WORKSPACE=$(ls -dt "$WORKSPACES_DIR"/sarah-* 2>/dev/null | head -1)
section "CONTRACTOR WORKSPACE · what Sarah's AI agent will see"
echo
echo "$(cyan "▸ Workspace at:") $WORKSPACE"
echo
echo "$(green "▸ Workspace structure")  $(dim "(76 files — sanitized + scope-filtered)")"
hr
ls "$WORKSPACE" | sed 's/^/  /'
echo
echo "$(green "▸ vibeguard-contractor-brief.md")  $(dim "(the rules Sarah's agent reads first)")"
hr
sed -n '1,30p' "$WORKSPACE/vibeguard-contractor-brief.md" | sed 's/^/  /'
echo "  $(dim "...(continues with hard rules + delivery expectations)")"
echo
echo "$(green "▸ Sarah's copy of src/lib/config.ts")  $(dim "(no real secrets — same env-var refactor)")"
hr
cat "$WORKSPACE/src/lib/config.ts" | sed 's/^/  /'
echo

read -r -p "Press Enter to see the KB (machine-readable state)..."

# ════════════════ KB ════════════════
section "KB · what VibeGuard remembers (~/.vibeguard/kb.json)"
echo
"$PY" -m json.tool "$KB_FILE" | head -40 | sed 's/^/  /'
echo "  $(dim "...truncated. full file at $KB_FILE")"
echo

# ════════════════ SUMMARY ════════════════
section "SUMMARY · what just happened"
echo
echo "  $(green "✓") VibeGuard scanned shopify-store and found 5 secrets in source"
echo "  $(green "✓") Refactored owner's real config.ts: secrets → process.env reads"
echo "  $(green "✓") Created .env.example (template)"
echo "  $(green "✓") Updated .gitignore so .env.local won't be committed"
echo "  $(green "✓") Cleaned up duplicate inline keys + leaky console.log in stripe_stuff.ts"
echo "  $(green "✓") Generated Sarah's sanitized workspace at:"
echo "     $WORKSPACE"
echo "  $(green "✓") Wrote vibeguard-owner-memory.md (owner side)"
echo "  $(green "✓") Wrote vibeguard-contractor-brief.md (inside the workspace)"
echo
echo "  $(yellow "◆") The owner's $(cyan "$DEMO_TARGET") is changed on disk — open it in any editor."
echo "  $(yellow "◆") Sarah can be sent the workspace folder; her AI agent will read"
echo "     the brief and respect the scope without ever seeing real secrets."
echo
echo "  To re-run from a clean state:  $(cyan "./scripts/see_it.sh")"
echo "  To open the changes in VS Code:"
echo "     $(cyan "code $DEMO_TARGET $WORKSPACE")"
echo
bold "🎬 done."
