import json
import pathlib
import tempfile
from core.patches import load_patch_set, patch_set_for_advisory


def test_load_patch_set_reads_manifest_and_patches():
    with tempfile.TemporaryDirectory() as tmp:
        patch_dir = pathlib.Path(tmp) / "fe_be_separation"
        patch_dir.mkdir()
        (patch_dir / "manifest.json").write_text(json.dumps({
            "name": "fe_be_separation",
            "advisory_id": "fe_be_separation",
            "patches": ["01-create.patch"],
        }))
        (patch_dir / "01-create.patch").write_text(
            "--- /dev/null\n+++ b/new_file.txt\n@@ -0,0 +1 @@\n+hello\n"
        )
        ps = load_patch_set(str(patch_dir))
        assert ps["name"] == "fe_be_separation"
        assert len(ps["patches"]) == 1
        assert "hello" in ps["patches"][0]["content"]


def test_patch_set_for_advisory_finds_matching_dir():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        d = root / "fe_be_separation"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "name": "fe_be_separation",
            "advisory_id": "fe_be_separation",
            "patches": ["p.patch"],
        }))
        (d / "p.patch").write_text("--- a\n+++ b\n")
        ps = patch_set_for_advisory(str(root), "fe_be_separation")
        assert ps is not None
        assert ps["name"] == "fe_be_separation"


def test_patch_set_for_advisory_returns_none_for_unknown_id():
    with tempfile.TemporaryDirectory() as tmp:
        ps = patch_set_for_advisory(str(tmp), "totally_unknown_advisory")
        assert ps is None


def test_patch_set_skips_empty_manifest():
    """Placeholder manifests with no patches should not be returned."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        d = root / "empty_set"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "name": "empty_set",
            "advisory_id": "empty_set",
            "patches": [],
        }))
        ps = patch_set_for_advisory(str(root), "empty_set")
        assert ps is None


def test_missing_patch_root_returns_none():
    ps = patch_set_for_advisory("/nonexistent/path/xyz", "anything")
    assert ps is None
