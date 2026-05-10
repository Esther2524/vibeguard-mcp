import json
import pathlib
import tempfile
from core.patches import load_patch_set, patch_set_for_answers


def test_load_patch_set_reads_manifest_and_patches():
    with tempfile.TemporaryDirectory() as tmp:
        patch_dir = pathlib.Path(tmp) / "fe_be_split"
        patch_dir.mkdir()
        (patch_dir / "manifest.json").write_text(json.dumps({
            "name": "fe_be_split",
            "trigger_question_id": "advisory_fe_be",
            "trigger_answer": "yes",
            "patches": ["01-create.patch"],
        }))
        (patch_dir / "01-create.patch").write_text(
            "--- /dev/null\n+++ b/new_file.txt\n@@ -0,0 +1 @@\n+hello\n"
        )
        ps = load_patch_set(str(patch_dir))
        assert ps["name"] == "fe_be_split"
        assert len(ps["patches"]) == 1
        assert "hello" in ps["patches"][0]["content"]


def test_patch_set_for_answers_matches_trigger():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        d = root / "fe_be_split"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "name": "fe_be_split",
            "trigger_question_id": "advisory_fe_be",
            "trigger_answer": "yes",
            "patches": ["p.patch"],
        }))
        (d / "p.patch").write_text("--- a\n+++ b\n")
        answers = [
            {"question_id": "persona_background", "answer": "non-tech"},
            {"question_id": "advisory_fe_be", "answer": "yes please"},
        ]
        ps = patch_set_for_answers(str(root), answers)
        assert ps is not None
        assert ps["name"] == "fe_be_split"


def test_patch_set_for_answers_returns_none_if_no_match():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        d = root / "fe_be_split"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "name": "fe_be_split",
            "trigger_question_id": "advisory_fe_be",
            "trigger_answer": "yes",
            "patches": ["p.patch"],
        }))
        (d / "p.patch").write_text("--- a\n+++ b\n")
        answers = [{"question_id": "advisory_fe_be", "answer": "no thanks"}]
        ps = patch_set_for_answers(str(root), answers)
        assert ps is None


def test_patch_set_skips_empty_manifest():
    """Placeholder manifests with no patches should not be returned."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        d = root / "empty_set"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "name": "empty_set",
            "trigger_question_id": "advisory_fe_be",
            "trigger_answer": "yes",
            "patches": [],
        }))
        answers = [{"question_id": "advisory_fe_be", "answer": "yes"}]
        ps = patch_set_for_answers(str(root), answers)
        assert ps is None


def test_missing_patch_root_returns_none():
    ps = patch_set_for_answers("/nonexistent/path/xyz", [])
    assert ps is None
