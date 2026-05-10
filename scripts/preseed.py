"""Run before each demo to ensure a clean, repeatable starting state.

Usage: python scripts/preseed.py [--soap-shop /path/to/soap-shop]
"""
import argparse
import os
import shutil
import subprocess
import sys

KB_FILE = os.path.expanduser("~/.vibeguard/kb.json")
WORKSPACES = os.path.expanduser("~/vibeguard-workspaces")


def reset(soap_shop: str | None) -> None:
    if os.path.exists(KB_FILE):
        os.unlink(KB_FILE)
        print(f"  removed {KB_FILE}")

    if os.path.exists(WORKSPACES):
        shutil.rmtree(WORKSPACES)
        print(f"  removed {WORKSPACES}")

    if soap_shop and os.path.isdir(soap_shop):
        try:
            subprocess.run(["git", "stash"], cwd=soap_shop, capture_output=True, check=False)
            subprocess.run(["git", "checkout", "main"], cwd=soap_shop, capture_output=True, check=False)
            subprocess.run(["git", "clean", "-fd"], cwd=soap_shop, capture_output=True, check=False)
            print(f"  reset {soap_shop} to clean main")
        except Exception as e:
            print(f"  warning: git reset failed for {soap_shop}: {e}", file=sys.stderr)

        leftover = os.path.join(soap_shop, "vibeguard-owner-memory.md")
        if os.path.exists(leftover):
            os.unlink(leftover)
            print(f"  removed leftover {leftover}")

    print("VibeGuard demo state reset. Ready to record.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset VibeGuard demo state.")
    parser.add_argument(
        "--soap-shop",
        default=None,
        help="Path to mock soap-shop repo to reset (optional).",
    )
    args = parser.parse_args()
    reset(args.soap_shop)


if __name__ == "__main__":
    main()
