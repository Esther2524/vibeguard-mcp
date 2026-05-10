"""Loader + applier for hardcoded refactor patch sets.

Patch sets live in `patches/<advisory_id>/` with a `manifest.json` listing
patch files. Each patch is in unified-diff format and is applied via
`git apply`.

The triggering rule (v0.3): a patch set is selected when its
`advisory_id` (which equals the patch directory name) appears in the
`approved_advisories` list passed to complete_handoff.
"""
import json
import os
import pathlib
import subprocess
import tempfile


def load_patch_set(patch_dir: str) -> dict:
    """Load a patch set manifest + all patch contents."""
    p = pathlib.Path(patch_dir)
    manifest = json.loads((p / "manifest.json").read_text())
    patches = []
    for patch_filename in manifest["patches"]:
        patch_path = p / patch_filename
        patches.append({
            "filename": patch_filename,
            "content": patch_path.read_text(),
        })
    manifest["patches"] = patches
    return manifest


def apply_patch_set(target_codebase: str, patch_set: dict) -> dict:
    """Apply a loaded patch set via `git apply`. Returns summary."""
    applied: list[str] = []
    failed: list[dict] = []
    for patch in patch_set["patches"]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as tf:
            tf.write(patch["content"])
            patch_file = tf.name
        try:
            result = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", patch_file],
                cwd=target_codebase,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                applied.append(patch["filename"])
            else:
                failed.append({"filename": patch["filename"], "stderr": result.stderr})
        finally:
            os.unlink(patch_file)
    return {"applied": applied, "failed": failed, "name": patch_set["name"]}


def patch_set_for_advisory(patch_root: str, advisory_id: str) -> dict | None:
    """Look up the patch set for a given advisory_id (patch directory name).

    Returns None if the advisory has no patch set or the manifest is empty
    (placeholder)."""
    root = pathlib.Path(patch_root)
    if not root.exists():
        return None
    patch_dir = root / advisory_id
    if not patch_dir.is_dir():
        return None
    manifest_file = patch_dir / "manifest.json"
    if not manifest_file.exists():
        return None
    try:
        manifest = json.loads(manifest_file.read_text())
    except json.JSONDecodeError:
        return None
    if not manifest.get("patches"):
        return None
    return load_patch_set(str(patch_dir))
