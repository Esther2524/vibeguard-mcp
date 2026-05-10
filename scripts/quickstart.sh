#!/usr/bin/env bash
# VibeGuard demo quickstart.
#
# What this does:
#   1. Verifies your local environment (venv, deps, demo target, MCP config)
#   2. Resets all VibeGuard state (kb.json, workspaces, demo target git state)
#   3. Optionally pre-warms the cache OR runs the full flow as a dry-run
#
# Usage:
#   ./scripts/quickstart.sh             # verify + reset (ready for live demo)
#   ./scripts/quickstart.sh dry-run     # verify + reset + run full flow (no Cursor needed)
#   ./scripts/quickstart.sh prewarm     # verify + reset + register_codebase only (warms KB)
#
# Override the demo target:
#   DEMO_TARGET=/path/to/your/repo ./scripts/quickstart.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_TARGET="${DEMO_TARGET:-/tmp/shopify-store-demo}"
KB_FILE="$HOME/.vibeguard/kb.json"
WORKSPACES_DIR="$HOME/vibeguard-workspaces"
CURSOR_MCP_CONFIG="$HOME/.cursor/mcp.json"
MODE="${1:-reset}"

bold()    { printf '\033[1m%s\033[0m\n' "$*"; }
ok()      { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn()    { printf '  \033[33m⚠\033[0m  %s\n' "$*"; }
fail()    { printf '  \033[31m✗\033[0m %s\n' "$*"; }
header()  { printf '\n\033[1;36m── %s ──\033[0m\n' "$*"; }

bold "🛡️  VibeGuard demo quickstart  (mode: $MODE)"
echo "    repo:        $REPO_ROOT"
echo "    demo target: $DEMO_TARGET"

# ─────────────────────────── 1. environment checks ───────────────────────────
header "1. environment checks"

if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
  fail "no venv at $REPO_ROOT/.venv"
  echo "      run:  cd $REPO_ROOT && python3 -m venv .venv && .venv/bin/pip install -e . pytest"
  exit 1
fi
PY="$REPO_ROOT/.venv/bin/python"
ok "venv: $REPO_ROOT/.venv"

if ! "$PY" -c "from mcp.server.fastmcp import FastMCP; from faker import Faker" 2>/dev/null; then
  fail "deps missing — run: $REPO_ROOT/.venv/bin/pip install -e ."
  exit 1
fi
ok "deps: mcp + faker importable"

if [[ ! -f "$CURSOR_MCP_CONFIG" ]]; then
  warn "no Cursor MCP config at $CURSOR_MCP_CONFIG (live demo won't work without it)"
elif grep -q vibeguard "$CURSOR_MCP_CONFIG"; then
  ok "Cursor MCP config has vibeguard entry"
else
  warn "Cursor MCP config exists but no 'vibeguard' entry — live demo won't trigger"
fi

# ─────────────────────────── 2. demo target ───────────────────────────
header "2. demo target"

if [[ ! -d "$DEMO_TARGET/.git" ]]; then
  warn "no demo target at $DEMO_TARGET"
  read -r -p "    clone https://github.com/ycecilia/shopify-store.git there? (y/n) " yn
  case "$yn" in
    [Yy]*)
      git clone --depth 1 https://github.com/ycecilia/shopify-store.git "$DEMO_TARGET"
      ok "cloned shopify-store → $DEMO_TARGET"
      ;;
    *)
      fail "no demo target. set DEMO_TARGET env var to your codebase path."
      exit 1
      ;;
  esac
else
  ok "demo target exists: $DEMO_TARGET"
fi

# ─────────────────────────── 3. reset all state ───────────────────────────
header "3. reset state"

if [[ -f "$KB_FILE" ]]; then
  rm -f "$KB_FILE"
  ok "removed $KB_FILE"
else
  ok "kb.json already clean"
fi

if [[ -d "$WORKSPACES_DIR" ]] && [[ -n "$(ls -A "$WORKSPACES_DIR" 2>/dev/null)" ]]; then
  rm -rf "$WORKSPACES_DIR"/*
  ok "wiped $WORKSPACES_DIR"
else
  ok "workspaces already clean"
fi

# Reset the demo target back to clean main + remove any leftover memory files
(
  cd "$DEMO_TARGET"
  git stash --include-untracked --quiet 2>/dev/null || true
  git stash drop 2>/dev/null || true
  git reset --hard HEAD --quiet
  git clean -fd --quiet
  rm -f vibeguard-owner-memory.md
)
ok "$DEMO_TARGET reset to clean main"

# ─────────────────────────── 4. mode-specific actions ───────────────────────────
case "$MODE" in
  reset)
    header "4. ready for live demo"
    echo "    in Cursor, on the demo machine:"
    echo "      \"register_codebase on $DEMO_TARGET\""
    echo "      \"I want to hand off the front-end to Sarah\""
    echo
    ;;

  prewarm)
    header "4. pre-warming KB (register_codebase only)"
    "$PY" -c "
import os, sys
sys.path.insert(0, '$REPO_ROOT')
from core.kb import KB
from tools.register import register_codebase_impl
kb = KB(os.path.expanduser('~/.vibeguard/kb.json'))
r = register_codebase_impl(kb, '$DEMO_TARGET')
print(f'  → {r[\"zones\"][\"SECRETS\"][\"count\"]} secrets, {r[\"zones\"][\"PII\"][\"count\"]} PII columns indexed')
print(f'  → kb.json populated; live start_handoff will be instant')
"
    ok "pre-warmed"
    ;;

  dry-run)
    header "4. running full dry-run (no Cursor needed)"
    "$PY" "$REPO_ROOT/scripts/dry_run.py" "$DEMO_TARGET"
    ;;

  *)
    fail "unknown mode: $MODE   (use: reset | prewarm | dry-run)"
    exit 1
    ;;
esac

bold "🎬 done."
