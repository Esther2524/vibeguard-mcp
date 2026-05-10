"""File copy + in-place secret substitution + scope filtering."""
import fnmatch
import pathlib
import shutil

SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__", ".next", "dist", "build", "vendor"}


def sanitize_to_workspace(
    src_root: str,
    dst_workspace: str,
    secrets_to_replace: list[dict],
    scope_files: list[str] | None,
) -> dict:
    """Copy src to dst, replacing real secret values with mock values.

    Args:
        src_root: directory to copy from
        dst_workspace: directory to copy to (created if needed)
        secrets_to_replace: list of {real_value, mock_value} dicts
        scope_files: optional glob list — only copy files matching any pattern.
                     If None, copy everything.

    Returns:
        {"files_copied": int, "mocks_applied": int}
    """
    src = pathlib.Path(src_root)
    dst = pathlib.Path(dst_workspace)
    dst.mkdir(parents=True, exist_ok=True)

    replacements = {s["real_value"]: s["mock_value"] for s in secrets_to_replace}
    mock_count = 0
    files_copied = 0

    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(src)
        rel_str = str(rel)
        if scope_files is not None:
            if not any(fnmatch.fnmatch(rel_str, glob) for glob in scope_files):
                continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = path.read_text(errors="ignore")
        except Exception:
            shutil.copy2(path, target)
            files_copied += 1
            continue

        new_content = content
        for real, mock in replacements.items():
            if real in new_content:
                new_content = new_content.replace(real, mock)
                mock_count += 1
        target.write_text(new_content)
        files_copied += 1

    return {"files_copied": files_copied, "mocks_applied": mock_count}
