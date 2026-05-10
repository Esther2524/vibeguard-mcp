import pathlib
import tempfile
from core.sanitizer import sanitize_to_workspace
from tests._fixtures import FAKE_STRIPE_LIVE


def test_sanitizes_secrets_in_copy():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = pathlib.Path(src_dir)
        dst = pathlib.Path(dst_dir) / "workspace"
        (src / ".env").write_text(f"STRIPE_KEY={FAKE_STRIPE_LIVE}\n")
        (src / "app.py").write_text("# safe code\nprint('hello')\n")
        secrets = [
            {"real_value": FAKE_STRIPE_LIVE,
             "mock_value": "sk_mock_VIBEGUARD_xxx"},
        ]
        result = sanitize_to_workspace(str(src), str(dst), secrets, scope_files=None)
        assert (dst / "app.py").exists()
        env_content = (dst / ".env").read_text()
        assert FAKE_STRIPE_LIVE not in env_content
        assert "sk_mock_VIBEGUARD_xxx" in env_content
        assert result["mocks_applied"] >= 1
        assert result["files_copied"] >= 2


def test_scope_filter_excludes_files():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = pathlib.Path(src_dir)
        dst = pathlib.Path(dst_dir) / "workspace"
        (src / "frontend.tsx").write_text("export default () => null;")
        (src / "backend.py").write_text("# secret backend logic")
        sanitize_to_workspace(str(src), str(dst), [], scope_files=["frontend.tsx"])
        assert (dst / "frontend.tsx").exists()
        assert not (dst / "backend.py").exists()


def test_scope_filter_glob_matches():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = pathlib.Path(src_dir)
        dst = pathlib.Path(dst_dir) / "workspace"
        (src / "app").mkdir()
        (src / "app" / "page.tsx").write_text("// frontend")
        (src / "app" / "api.ts").write_text("// also frontend-ish")
        (src / "backend.py").write_text("// backend")
        sanitize_to_workspace(str(src), str(dst), [], scope_files=["app/*"])
        assert (dst / "app" / "page.tsx").exists()
        assert (dst / "app" / "api.ts").exists()
        assert not (dst / "backend.py").exists()


def test_skips_node_modules():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = pathlib.Path(src_dir)
        dst = pathlib.Path(dst_dir) / "workspace"
        (src / "app.py").write_text("# main code")
        nm = src / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "junk.js").write_text("// dont copy")
        sanitize_to_workspace(str(src), str(dst), [], scope_files=None)
        assert (dst / "app.py").exists()
        assert not (dst / "node_modules").exists()
