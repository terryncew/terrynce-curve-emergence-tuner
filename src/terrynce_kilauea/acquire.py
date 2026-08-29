from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from .hashing import digest
from .protocol import repo_root


def _download(url: str, dst: Path, retries: int = 4) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TERRYNCE-KILAUEA-001/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r, tmp.open("wb") as f:
                while True:
                    chunk = r.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.replace(dst)
            return
        except Exception:
            if tmp.exists():
                tmp.unlink()
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def acquire(root: Path | None = None, force: bool = False) -> list[dict]:
    root = root or repo_root()
    lock = json.loads((root / "config" / "sources.lock.json").read_text())
    out = []
    for spec in lock["dataset_record"]["files"]:
        dst = root / "data" / "raw" / spec["name"]
        if force or not dst.exists():
            _download(spec["url"], dst)
        md5 = digest(dst, "md5")
        sha256 = digest(dst, "sha256")
        ok = md5.lower() == spec["md5"].lower()
        out.append({
            "name": spec["name"],
            "path": str(dst),
            "bytes": dst.stat().st_size,
            "expected_md5": spec["md5"],
            "md5": md5,
            "sha256": sha256,
            "verified": ok,
            "source_url": spec["url"],
        })
        if not ok:
            raise RuntimeError(f"Hash mismatch for {spec['name']}: expected {spec['md5']}, got {md5}")
    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "receipts.json").write_text(json.dumps(out, indent=2))
    return out
