"""Loader + applier for hardcoded refactor patch sets.

Patch sets live in `patches/<name>/` with a `manifest.json` listing
patch files. Each patch is in unified-diff format and is applied via
`git apply`.
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


def patch_set_for_answers(patch_root: str, answers: list[dict]) -> dict | None:
    """Look at all patch sets in `patch_root`, find one whose trigger matches answers."""
    root = pathlib.Path(patch_root)
    if not root.exists():
        return None
    for patch_dir in root.iterdir():
        if not patch_dir.is_dir():
            continue
        manifest_file = patch_dir / "manifest.json"
        if not manifest_file.exists():
            continue
        try:
            manifest = json.loads(manifest_file.read_text())
        except json.JSONDecodeError:
            continue
        # Skip placeholder/empty manifests
        if not manifest.get("patches"):
            continue
        trigger_qid = manifest.get("trigger_question_id")
        trigger_ans = manifest.get("trigger_answer", "yes")
        for ans in answers:
            if (
                ans.get("question_id") == trigger_qid
                and ans.get("answer", "").lower().startswith(trigger_ans.lower())
            ):
                return load_patch_set(str(patch_dir))
    return None
