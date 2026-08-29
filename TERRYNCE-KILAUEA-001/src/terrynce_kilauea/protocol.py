from __future__ import annotations

import hashlib
import json
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_protocol(root: Path | None = None) -> dict:
    root = root or repo_root()
    return json.loads((root / "config" / "frozen_protocol.json").read_text())


def canonical_json(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def protocol_sha256(root: Path | None = None) -> str:
    return hashlib.sha256(canonical_json(load_protocol(root))).hexdigest()
