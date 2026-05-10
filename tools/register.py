"""Implementation of the `register_codebase` MCP tool."""
from core.classifier import scan_codebase
from core.faker_mocks import mock_for_secret
from core.kb import KB


def register_codebase_impl(kb: KB, codebase_path: str) -> dict:
    """Scan codebase, classify, store in KB with mocks, return summary."""
    scan = scan_codebase(codebase_path)
    manifest_id = kb.create_manifest(codebase_path)

    # Pre-compute mocks for each detected secret so subsequent steps don't need an LLM
    enriched_secrets = []
    for s in scan["secrets"]:
        mock = mock_for_secret(s["kind"], s["value"])
        enriched_secrets.append({**s, "mock_value": mock})
    kb.add_secrets(manifest_id, enriched_secrets)

    kb.add_pii(manifest_id, scan["pii"])

    return {
        "manifest_id": manifest_id,
        "zones": {
            "SECRETS": {
                "count": len(scan["secrets"]),
                "items": [{"file": s["file"], "kind": s["kind"], "locator": s["locator"]} for s in scan["secrets"]],
            },
            "PII": {
                "count": len(scan["pii"]),
                "items": [{"file": p["file"], "kind": p["kind"], "locator": p["locator"]} for p in scan["pii"]],
            },
            "BUSINESS_LOGIC": {"count": 0, "items": []},
            "SAFE_TO_SHARE": {"count": 0},
        },
        "warnings": [],
    }
