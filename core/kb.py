"""JSON-backed Knowledge Base for VibeGuard.

Stores codebase classifications + handoff state in a single JSON file.
Single-writer assumption: only the owner's MCP server writes to it.
Atomic-ish writes via tmp+rename so judges always see consistent state.
"""
import json
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any

EMPTY_KB = {"manifests": {}, "handoffs": {}}


class KB:
    def __init__(self, json_path: str):
        self.path = pathlib.Path(json_path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write(EMPTY_KB)

    def _read(self) -> dict:
        return json.loads(self.path.read_text())

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        tmp.replace(self.path)

    # ---------------- manifests ----------------

    def create_manifest(self, codebase_path: str) -> str:
        data = self._read()
        manifest_id = str(uuid.uuid4())
        data["manifests"][manifest_id] = {
            "id": manifest_id,
            "codebase_path": codebase_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "secrets": [],
            "pii": [],
        }
        self._write(data)
        return manifest_id

    def get_manifest(self, manifest_id: str) -> dict | None:
        return self._read()["manifests"].get(manifest_id)

    def latest_manifest_id(self) -> str | None:
        data = self._read()
        if not data["manifests"]:
            return None
        return max(data["manifests"].items(), key=lambda kv: kv[1]["created_at"])[0]

    # ---------------- secrets / PII ----------------

    def add_secrets(self, manifest_id: str, items: list[dict[str, Any]]) -> None:
        data = self._read()
        for it in items:
            data["manifests"][manifest_id]["secrets"].append({
                "file": it["file"],
                "locator": it["locator"],
                "kind": it["kind"],
                "value": it["value"],
                "mock_value": it.get("mock_value"),
                "confidence": it.get("confidence", 1.0),
            })
        self._write(data)

    def get_secrets(self, manifest_id: str) -> list[dict]:
        return list(self._read()["manifests"][manifest_id].get("secrets", []))

    def add_pii(self, manifest_id: str, items: list[dict]) -> None:
        data = self._read()
        for it in items:
            data["manifests"][manifest_id]["pii"].append({
                "file": it["file"],
                "locator": it["locator"],
                "kind": it["kind"],
                "confidence": it.get("confidence", 1.0),
            })
        self._write(data)

    def get_pii(self, manifest_id: str) -> list[dict]:
        return list(self._read()["manifests"][manifest_id].get("pii", []))

    def set_mock_for(self, manifest_id: str, real_value: str, mock_value: str) -> None:
        data = self._read()
        for s in data["manifests"][manifest_id]["secrets"]:
            if s["value"] == real_value:
                s["mock_value"] = mock_value
        self._write(data)

    # ---------------- handoffs ----------------

    def create_handoff(self, manifest_id: str, contractor_id: str, intent: str) -> str:
        data = self._read()
        hid = str(uuid.uuid4())[:8]
        data["handoffs"][hid] = {
            "id": hid,
            "manifest_id": manifest_id,
            "contractor_id": contractor_id,
            "intent": intent,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "answers_json": None,
            "workspace_path": None,
        }
        self._write(data)
        return hid

    def save_handoff_answers(self, handoff_id: str, answers_json: str, workspace_path: str) -> None:
        data = self._read()
        data["handoffs"][handoff_id]["answers_json"] = answers_json
        data["handoffs"][handoff_id]["workspace_path"] = workspace_path
        self._write(data)

    def get_handoff(self, handoff_id: str) -> dict | None:
        return self._read()["handoffs"].get(handoff_id)
