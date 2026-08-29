from __future__ import annotations

import csv
from pathlib import Path
import numpy as np

from .canonical import Cycle
from .signal import SignalFit, fit_signal, predict_duration


def previous_cycle_predictions(cycles: list[Cycle], train_n: int, decision_times: dict[str, list[float]]) -> dict[tuple[int, float], float]:
    out = {}
    for i in range(train_n, len(cycles)):
        prev_duration = cycles[i - 1].duration_hours
        for t in decision_times[cycles[i].cycle_id]:
            out[(i, float(t))] = prev_duration
    return out


def choose_best_single_sensor(train: list[Cycle], protocol: dict, sensors: list[str] | None = None) -> tuple[str, SignalFit, dict]:
    sensors = sensors or list(train[0].sensors)
    checkpoint = 12.0
    scores = {}
    fits = {}
    for s in sensors:
        fit = fit_signal(train, [s], protocol)
        fits[s] = fit
        errs = []
        for c in train:
            if c.duration_hours > checkpoint + 1.0 and c.time_hours[-1] >= checkpoint:
                pred, _ = predict_duration(c, checkpoint, fit)
                if np.isfinite(pred):
                    errs.append(abs(pred - c.duration_hours))
        scores[s] = float(np.mean(errs)) if errs else float("inf")
    winner = min(scores, key=scores.get)
    return winner, fits[winner], scores


def load_gnn_csv(path: Path) -> dict[tuple[str, float], float]:
    out = {}
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        required = {"cycle_id", "time_hours", "predicted_duration_hours"}
        if not r.fieldnames or not required.issubset(r.fieldnames):
            raise ValueError(f"GNN CSV must contain {sorted(required)}")
        for row in r:
            out[(row["cycle_id"], round(float(row["time_hours"]), 8))] = float(row["predicted_duration_hours"])
    return out
