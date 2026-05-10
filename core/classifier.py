"""Regex + schema-based classifier for secrets and PII columns."""
import pathlib
import re

SECRET_PATTERNS = [
    ("stripe_secret_key", re.compile(r"sk_live_[A-Za-z0-9]{20,}"), 1.0),
    ("stripe_test_key",   re.compile(r"sk_test_[A-Za-z0-9]{20,}"), 0.6),
    ("aws_access_key",    re.compile(r"AKIA[A-Z0-9]{16}"),         1.0),
    ("openai_api_key",    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"), 1.0),
    ("github_pat",        re.compile(r"ghp_[A-Za-z0-9]{20,}"),     1.0),
    ("postgres_url",      re.compile(r"postgres(?:ql)?://[^\s'\"]+"), 0.95),
    ("generic_jwt",       re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), 0.85),
    ("anthropic_key",     re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), 1.0),
    ("private_key_pem",   re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), 1.0),
    ("slack_token",       re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), 1.0),
]

PII_COLUMN_NAMES = {
    "email", "phone", "ssn", "address", "name", "first_name", "last_name",
    "dob", "date_of_birth", "credit_card", "creditcard", "card_number",
    "passport", "driver_license", "tax_id",
}

SQL_COLUMN_RE = re.compile(
    r"^\s*([a-z_][a-z0-9_]*)\s+(TEXT|VARCHAR|CHAR|STRING|JSON|JSONB)",
    re.IGNORECASE | re.MULTILINE,
)

SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".env", ".json",
    ".yaml", ".yml", ".sql", ".sh", ".toml", ".ini", ".cfg",
}
SCAN_DOTFILES = {".env", ".env.local", ".env.production", ".env.development"}
SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__", ".next", "dist", "build", "vendor"}


def find_secrets(content: str, file: str) -> list[dict]:
    hits = []
    for kind, pattern, base_confidence in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            hits.append({
                "file": file,
                "locator": f"L{line_no}",
                "kind": kind,
                "value": match.group(0),
                "confidence": base_confidence,
            })
    return hits


def find_pii_columns(sql_content: str, file: str) -> list[dict]:
    hits = []
    for match in SQL_COLUMN_RE.finditer(sql_content):
        col_name = match.group(1).lower()
        if col_name in PII_COLUMN_NAMES:
            line_no = sql_content[:match.start()].count("\n") + 1
            hits.append({
                "file": file,
                "locator": f"L{line_no}:{col_name}",
                "kind": col_name,
                "confidence": 1.0,
            })
    return hits


def scan_codebase(root: str) -> dict:
    """Walk a codebase, return {secrets: [...], pii: [...]}."""
    secrets, pii = [], []
    root_path = pathlib.Path(root)
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in SCAN_EXTENSIONS and path.name not in SCAN_DOTFILES:
            continue
        try:
            content = path.read_text(errors="ignore")
        except Exception:
            continue
        rel = str(path.relative_to(root_path))
        secrets.extend(find_secrets(content, rel))
        if path.suffix == ".sql":
            pii.extend(find_pii_columns(content, rel))
    return {"secrets": secrets, "pii": pii}
