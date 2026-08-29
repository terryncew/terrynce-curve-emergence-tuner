from __future__ import annotations

import csv
from pathlib import Path
import numpy as np


def make_fixture(path: Path, n_cycles: int = 39, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        sensors = ["gps_AHUP","gps_BYRL","gps_CRIM","gps_OUTL","gps_UWEV","tilt"]
        w.writerow(["cycle_id","time_hours","duration_hours",*sensors])
        for i in range(n_cycles):
            duration = 24 + 0.45 * i + rng.normal(0, 1.0)
            tau = 5.5 + 0.08 * i
            t = np.arange(0, max(duration - 0.2, 0.5), 1/6)  # 10-min samples
            amps = np.asarray([1.0,0.8,1.2,0.7,1.1,1.3])
            for ti in t:
                base = (1 - np.exp(-ti / tau))
                vals = amps * base + rng.normal(0, 0.015, size=len(amps))
                w.writerow([f"{i+1:02d}", f"{ti:.8f}", f"{duration:.8f}", *[f"{v:.8f}" for v in vals]])
