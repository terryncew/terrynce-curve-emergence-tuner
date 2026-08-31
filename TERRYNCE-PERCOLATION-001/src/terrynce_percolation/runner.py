from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from .core import KNOWN_PC, add_terrynce_score, aggregate, summarize

DEFAULT_FAMILIES = ["square_bond", "square_site", "triangular_site"]
DEFAULT_SIZES = [16, 24, 32, 48]


def p_grid(start: float = 0.35, stop: float = 0.75, step: float = 0.01) -> list[float]:
    count = int(round((stop - start) / step))
    return [round(start + i * step, 10) for i in range(count + 1)]


def protocol_sha256(protocol_path: Path) -> str:
    return hashlib.sha256(protocol_path.read_bytes()).hexdigest()


def run(output_dir: Path, protocol_path: Path, *, replicas: int = 32, sizes: list[int] | None = None,
        families: list[str] | None = None, seed: int = 20260831, grid: list[float] | None = None) -> dict:
    sizes = sizes or DEFAULT_SIZES
    families = families or DEFAULT_FAMILIES
    grid = grid or p_grid()
    for family in families:
        if family not in KNOWN_PC:
            raise ValueError(f"unknown family {family}")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for fi, family in enumerate(families):
        for n in sizes:
            for pi, p in enumerate(grid):
                rows.append(aggregate(family, n, p, replicas, seed + fi * 10_000_000 + n * 100_000 + pi * 1000))
    rows = add_terrynce_score(rows)
    summary = summarize(rows, families, sizes)
    summary["protocol_sha256"] = protocol_sha256(protocol_path)
    summary["run_config"] = {"families": families, "sizes": sizes, "replicas": replicas, "seed": seed, "p_grid": grid}

    raw_path = output_dir / "raw.csv"
    with raw_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schema": "terrynce.percolation.receipt.v1",
        "protocol_sha256": summary["protocol_sha256"],
        "summary_sha256": hashlib.sha256((output_dir / "summary.json").read_bytes()).hexdigest(),
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return summary
