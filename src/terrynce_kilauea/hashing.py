from __future__ import annotations

import hashlib
from pathlib import Path


def digest(path: Path, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()
