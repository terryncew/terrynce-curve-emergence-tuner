from __future__ import annotations

import csv
import json
import re
from pathlib import Path
import numpy as np

from .baselines import choose_best_single_sensor, load_gnn_csv
from .canonical import Cycle, load_csv, validate_cycles
from .protocol import load_protocol, protocol_sha256, repo_root
from .scoring import PredictionRow, calibrate_threshold, point_metrics, warning_metrics
from .signal import fit_signal, predict_duration


def decision_times(c: Cycle, protocol: dict) -> list[float]:
    start = protocol["decision_grid"]["start_hours"]
    step = protocol["decision_grid"]["step_minutes"] / 60.0
    end = c.duration_hours - protocol["decision_grid"]["stop_before_failure_hours"]
    if end < start:
        return []
    n = int(np.floor((end - start) / step)) + 1
    return [float(start + i * step) for i in range(n)]


def _fit_and_rows(cycles: list[Cycle], protocol: dict, gnn_path: Path | None = None) -> tuple[dict[str, list[PredictionRow]], dict]:
    ntrain = protocol["split"]["train_cycles"]
    train, test = cycles[:ntrain], cycles[ntrain:]
    all_sensors = list(train[0].sensors)
    sensors = [s for s in all_sensors if re.search(r"gps|gnss|tilt|ahup|byrl|crim|outl|uwev", s, re.I)]
    if len(sensors) < 2:
        raise ValueError("frozen Terrynce signal requires at least two deformation channels (GPS/GNSS/tilt names)")
    joint_fit = fit_signal(train, sensors, protocol)
    single_name, single_fit, single_scores = choose_best_single_sensor(train, protocol, sensors=sensors)

    rows: dict[str, list[PredictionRow]] = {"previous_cycle_timing": [], "best_single_sensor": [], "terrynce_joint_load_relief": []}
    if gnn_path:
        rows["published_gnn"] = []
        gnn = load_gnn_csv(gnn_path)
    else:
        gnn = {}

    # Training rows for threshold calibration (previous-cycle has valid history from cycle 2 onward).
    train_rows: dict[str, list[PredictionRow]] = {k: [] for k in rows}
    for i, c in enumerate(train):
        for t in decision_times(c, protocol):
            if i > 0:
                train_rows["previous_cycle_timing"].append(PredictionRow(c.cycle_id, "previous_cycle_timing", t, c.duration_hours, train[i-1].duration_hours))
            p1, _ = predict_duration(c, t, single_fit)
            pj, _ = predict_duration(c, t, joint_fit)
            train_rows["best_single_sensor"].append(PredictionRow(c.cycle_id, "best_single_sensor", t, c.duration_hours, p1))
            train_rows["terrynce_joint_load_relief"].append(PredictionRow(c.cycle_id, "terrynce_joint_load_relief", t, c.duration_hours, pj))
            if gnn_path:
                key = (c.cycle_id, round(t, 8))
                if key in gnn:
                    train_rows["published_gnn"].append(PredictionRow(c.cycle_id, "published_gnn", t, c.duration_hours, gnn[key]))

    # Strict chronological holdout. Previous completed holdout cycle becomes available history.
    all_history = cycles[:]
    for i in range(ntrain, len(cycles)):
        c = cycles[i]
        for t in decision_times(c, protocol):
            rows["previous_cycle_timing"].append(PredictionRow(c.cycle_id, "previous_cycle_timing", t, c.duration_hours, all_history[i-1].duration_hours))
            p1, _ = predict_duration(c, t, single_fit)
            pj, _ = predict_duration(c, t, joint_fit)
            rows["best_single_sensor"].append(PredictionRow(c.cycle_id, "best_single_sensor", t, c.duration_hours, p1))
            rows["terrynce_joint_load_relief"].append(PredictionRow(c.cycle_id, "terrynce_joint_load_relief", t, c.duration_hours, pj))
            if gnn_path:
                key = (c.cycle_id, round(t, 8))
                if key in gnn:
                    rows["published_gnn"].append(PredictionRow(c.cycle_id, "published_gnn", t, c.duration_hours, gnn[key]))

    fit_meta = {"joint_deformation_sensors": sensors, "excluded_sensor_columns": [s for s in all_sensors if s not in sensors], "best_single_sensor": single_name, "single_sensor_training_checkpoint_mae": single_scores}
    return rows, {"train_rows": train_rows, "fit_meta": fit_meta}


def replay(csv_path: Path, gnn_path: Path | None = None, root: Path | None = None) -> dict:
    root = root or repo_root()
    protocol = load_protocol(root)
    cycles = load_csv(csv_path)
    valid = validate_cycles(cycles, protocol["split"]["n_cycles"])
    if valid["status"] != "PASS":
        raise ValueError("canonical data validation failed: " + "; ".join(valid["issues"]))
    rows, aux = _fit_and_rows(cycles, protocol, gnn_path)
    warning = protocol["warning"]
    report = {
        "experiment_id": protocol["experiment_id"],
        "protocol_sha256": protocol_sha256(root),
        "data": valid,
        "fit": aux["fit_meta"],
        "models": {},
    }
    for model, test_rows in rows.items():
        train_rows = aux["train_rows"][model]
        cal = calibrate_threshold(train_rows, warning["target_horizon_hours"], warning["training_false_positive_rate_cap"])
        report["models"][model] = {
            "status": "AVAILABLE" if test_rows else "UNAVAILABLE",
            "threshold_calibration": cal,
            "point_forecast": point_metrics(test_rows, protocol["fixed_point_forecast_hours"]),
            "warning": warning_metrics(test_rows, cal["threshold"], warning["target_horizon_hours"], warning["persistence_steps"]) if test_rows else None,
        }
    if not gnn_path:
        report["models"]["published_gnn"] = {"status": "UNAVAILABLE", "reason": "No causal GNN prediction CSV supplied; no paper-table substitution allowed."}

    # Fail-closed conclusion: a tie is not a win.
    def mae12(name: str):
        try:
            return report["models"][name]["point_forecast"]["12.0"]["mae_hours"]
        except Exception:
            return None
    joint = mae12("terrynce_joint_load_relief")
    competitors = {k: mae12(k) for k in ("previous_cycle_timing", "best_single_sensor", "published_gnn")}
    available = {k:v for k,v in competitors.items() if v is not None}
    if joint is not None and available:
        best_name = min(available, key=available.get)
        report["decision_12h"] = {
            "joint_mae_hours": joint,
            "best_competitor": best_name,
            "best_competitor_mae_hours": available[best_name],
            "verdict": "PASS_JOINT_ADDS_VALUE" if joint < available[best_name] else "FAIL_OR_TIE",
        }
    else:
        report["decision_12h"] = {"verdict": "INCOMPLETE"}

    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "replay_report.json").write_text(json.dumps(report, indent=2))
    # machine-readable predictions
    with (artifacts / "holdout_predictions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model","cycle_id","time_hours","true_duration_hours","predicted_duration_hours"])
        for model, rr in rows.items():
            for r in rr:
                w.writerow([model, r.cycle_id, f"{r.time_hours:.8g}", f"{r.true_duration_hours:.8g}", f"{r.predicted_duration_hours:.8g}"])
    return report
