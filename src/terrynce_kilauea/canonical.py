from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


META = {"cycle_id", "time_hours", "duration_hours"}


@dataclass(frozen=True)
class Cycle:
    cycle_id: str
    time_hours: np.ndarray
    duration_hours: float
    sensors: dict[str, np.ndarray]


def load_csv(path: Path) -> list[Cycle]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not META.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain {sorted(META)}")
        sensor_names = [c for c in reader.fieldnames if c not in META]
        if not sensor_names:
            raise ValueError("CSV has no sensor columns")
        rows = list(reader)
    seen_order: list[str] = []
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        cid = r["cycle_id"]
        if cid not in grouped:
            grouped[cid] = []
            seen_order.append(cid)
        grouped[cid].append(r)
    cycles = []
    for cid in seen_order:
        rr = grouped[cid]
        t = np.asarray([float(x["time_hours"]) for x in rr], dtype=float)
        dur_values = {float(x["duration_hours"]) for x in rr}
        if len(dur_values) != 1:
            raise ValueError(f"cycle {cid}: duration_hours is not constant")
        sensors = {s: np.asarray([float(x[s]) for x in rr], dtype=float) for s in sensor_names}
        order = np.argsort(t, kind="stable")
        cycles.append(Cycle(cid, t[order], dur_values.pop(), {k: v[order] for k, v in sensors.items()}))
    return cycles


def validate_cycles(cycles: list[Cycle], expected: int = 39) -> dict:
    issues = []
    if len(cycles) != expected:
        issues.append(f"expected {expected} cycles, found {len(cycles)}")
    if cycles:
        sensor_set = set(cycles[0].sensors)
        for c in cycles:
            if set(c.sensors) != sensor_set:
                issues.append(f"cycle {c.cycle_id}: sensor columns differ")
            if len(c.time_hours) < 2 or np.any(np.diff(c.time_hours) <= 0):
                issues.append(f"cycle {c.cycle_id}: times must be strictly increasing")
            if c.time_hours[0] < -1e-9:
                issues.append(f"cycle {c.cycle_id}: negative elapsed time")
            if c.duration_hours <= c.time_hours[0]:
                issues.append(f"cycle {c.cycle_id}: invalid duration")
            for name, x in c.sensors.items():
                if x.shape != c.time_hours.shape:
                    issues.append(f"cycle {c.cycle_id}/{name}: shape mismatch")
                if not np.isfinite(x).all():
                    issues.append(f"cycle {c.cycle_id}/{name}: non-finite values")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues, "n_cycles": len(cycles), "sensors": sorted(cycles[0].sensors) if cycles else []}
