from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import numpy as np

from .protocol import load_protocol, protocol_sha256, repo_root
from .realdata import load_all_cycles
from .replay import decision_times
from .scoring import PredictionRow, point_metrics, warning_metrics
from .signal import SignalFit, predict_duration


def _fit_from_json(d: dict) -> SignalFit:
    return SignalFit(
        sensors=list(d["sensors"]),
        signs={k: float(v) for k, v in d["signs"].items()},
        scales={k: float(v) for k, v in d["scales"].items()},
        early_rates={k: float(v) for k, v in d["early_rates"].items()},
        x_mean=np.asarray(d["x_mean"], float),
        x_scale=np.asarray(d["x_scale"], float),
        beta=np.asarray(d["beta"], float),
        ridge_lambda=float(d["ridge_lambda"]),
    )


def _rows(cycles, start_idx: int, model: str, fit: SignalFit | None, proto: dict):
    out = []
    for i in range(start_idx, len(cycles)):
        c = cycles[i]
        for t in decision_times(c, proto):
            if model == "previous_cycle_timing":
                pred = float(cycles[i - 1].duration_hours)
            else:
                pred, _ = predict_duration(c, t, fit)
            out.append(PredictionRow(c.cycle_id, model, t, c.duration_hours, pred))
    return out


def replay_frozen_real(root: Path | None = None) -> dict:
    root = root or repo_root()
    proto = load_protocol(root)
    ntrain = int(proto["split"]["train_cycles"])
    ntotal = int(proto["split"]["n_cycles"])

    cal_path = root / "artifacts" / "frozen_calibration_receipt.json"
    mat = root / "data" / "raw" / "Kilauea_training_data.mat"
    if not cal_path.exists():
        raise FileNotFoundError("frozen calibration receipt missing")
    if not mat.exists():
        raise FileNotFoundError("published MAT file missing")

    cal_bytes = cal_path.read_bytes()
    cal = json.loads(cal_bytes)
    if cal["status"] != "PASS":
        raise ValueError("calibration receipt is not PASS")
    if cal["split"]["training_cycles"] != [1, ntrain]:
        raise ValueError("training split receipt mismatch")
    if cal["split"]["holdout_cycles"] != [ntrain + 1, ntotal]:
        raise ValueError("holdout split receipt mismatch")
    if cal.get("holdout_used_for_fit_or_threshold_selection") is not False:
        raise ValueError("holdout exclusion receipt missing")
    if cal["protocol_sha256"] != protocol_sha256(root):
        raise ValueError("protocol changed after calibration")

    cycles, adapter = load_all_cycles(mat, train_n=ntrain, n_cycles=ntotal)
    if len(cycles) != ntotal:
        raise ValueError(f"expected {ntotal} cycles, got {len(cycles)}")

    joint_fit = _fit_from_json(cal["joint_fit"])
    single_fit = _fit_from_json(cal["best_single_sensor"]["fit"])
    thresholds = cal["warning_thresholds"]

    models = {}
    prediction_sets = {}
    for model, fit in [
        ("previous_cycle_timing", None),
        ("best_single_sensor", single_fit),
        ("terrynce_joint_load_relief", joint_fit),
    ]:
        rr = _rows(cycles, ntrain, model, fit, proto)
        prediction_sets[model] = rr
        models[model] = {
            "status": "AVAILABLE",
            "point_forecast": point_metrics(rr, proto["fixed_point_forecast_hours"]),
            "warning": warning_metrics(
                rr,
                float(thresholds[model]["threshold"]),
                float(proto["warning"]["target_horizon_hours"]),
                int(proto["warning"]["persistence_steps"]),
            ),
            "frozen_training_threshold": thresholds[model],
        }

    models["published_gnn"] = {
        "status": "PENDING_REPRODUCTION",
        "reason": "Must be reproduced on the same 29/10 split and causal decision grid; paper-table substitution is forbidden.",
    }

    comparisons = {}
    for cp in ("12.0", "24.0"):
        j = models["terrynce_joint_load_relief"]["point_forecast"][cp]["mae_hours"]
        vals = {
            m: models[m]["point_forecast"][cp]["mae_hours"]
            for m in ("previous_cycle_timing", "best_single_sensor")
        }
        vals = {k: v for k, v in vals.items() if v is not None}
        best_name = min(vals, key=vals.get) if vals else None
        comparisons[cp] = {
            "joint_mae_hours": j,
            "best_conventional_baseline": best_name,
            "best_conventional_mae_hours": vals.get(best_name) if best_name else None,
            "joint_beats_conventional": bool(j is not None and best_name is not None and j < vals[best_name]),
        }

    report = {
        "experiment_id": proto["experiment_id"],
        "stage": "HELD_OUT_REPLAY_PHASE_A",
        "status": "COMPLETE_THREE_WAY_GNN_PENDING",
        "protocol_sha256": protocol_sha256(root),
        "calibration_receipt_sha256": hashlib.sha256(cal_bytes).hexdigest(),
        "split": {"training_cycles": [1, ntrain], "holdout_cycles": [ntrain + 1, ntotal]},
        "adapter": adapter.__dict__,
        "holdout_cycle_durations_hours": [float(c.duration_hours) for c in cycles[ntrain:]],
        "models": models,
        "comparisons": comparisons,
        "final_preregistered_verdict": "WITHHELD_PENDING_PUBLISHED_GNN",
        "boundary": "Cycles 30-39 are now opened. No coefficient, sensor choice, threshold, preprocessing rule, or protocol term may change under TERRYNCE-KILAUEA-001.",
    }

    outdir = root / "artifacts"
    outdir.mkdir(exist_ok=True)
    rp = outdir / "heldout_phase_a_report.json"
    rp.write_text(json.dumps(report, indent=2) + "\n")
    (outdir / "heldout_phase_a_report.sha256").write_text(
        hashlib.sha256(rp.read_bytes()).hexdigest() + "  heldout_phase_a_report.json\n"
    )

    with (outdir / "heldout_phase_a_predictions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "cycle_id", "time_hours", "true_duration_hours", "predicted_duration_hours"])
        for model, rr in prediction_sets.items():
            for r in rr:
                w.writerow([model, r.cycle_id, r.time_hours, r.true_duration_hours, r.predicted_duration_hours])
    return report
