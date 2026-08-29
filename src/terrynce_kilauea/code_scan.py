from __future__ import annotations

import ast
import json
import re
from pathlib import Path


PATTERNS = {
    "split_29": r"\b29\b",
    "last_10": r"\b10\b",
    "normalization_words": r"normaliz|standard|mean\(|std\(|median\(|quantile|percentile",
    "shuffle_or_permute": r"shuffle|permut|random_split",
    "validation_words": r"valid|test|holdout",
    "loadmat": r"loadmat|h5py|\.mat",
}


def scan_python(path: Path) -> dict:
    text = path.read_text(errors="replace")
    hits = {}
    lines = text.splitlines()
    for key, pat in PATTERNS.items():
        rx = re.compile(pat, re.I)
        hits[key] = [
            {"line": i + 1, "text": line[:300]}
            for i, line in enumerate(lines) if rx.search(line)
        ][:80]
    try:
        tree = ast.parse(text)
        syntax_ok = True
        calls = sorted({
            (n.func.id if isinstance(n.func, ast.Name) else n.func.attr)
            for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, (ast.Name, ast.Attribute))
        })
    except SyntaxError:
        syntax_ok = False
        calls = []
    return {"path": str(path), "syntax_ok": syntax_ok, "pattern_hits": hits, "call_names": calls}


def write_scan(paths: list[Path], out: Path) -> dict:
    report = {p.name: scan_python(p) for p in paths if p.exists()}
    out.write_text(json.dumps(report, indent=2))
    return report
