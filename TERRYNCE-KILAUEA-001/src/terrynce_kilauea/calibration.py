from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np

from .baselines import choose_best_single_sensor
from .protocol import load_protocol, protocol_sha256, repo_root
from .realdata import load_training_cycles
from .replay import decision_times
from .scoring import PredictionRow, calibrate_threshold
from .signal import fit_signal, predict_duration

DEFORMATION = ["gps_0", "gps_1", "gps_2", "gps_3", "gps_4", "tilt"]


def _json_fit(fit) -> dict:
    return {
        "sensors": fit.sensors,
        "signs": fit.signs,
        "scales": fit.scales,
        "early_rates": fit.early_rates,
        "x_mean": fit.x_mean.tolist(),
        "x_scale": fit.x_scale.tolist(),
        "beta": fit.beta.tolist(),
        "ridge_lambda": fit.ridge_lambda,
    }


def _rows(cycles, fit, model, protocol):
    rows = []
    for c in cycles:
        for t in decision_times(c, protocol):
            pred, _ = predict_duration(c, t, fit)
            rows.append(PredictionRow(c.cycle_id, model, t, c.duration_hours, pred))
    return rows


def calibrate_real(root: Path | None = None) -> dict:
    root = root or repo_root()
    proto = load_protocol(root)
    ntrain = int(proto["split"]["train_cycles"])
    mat = root / "data" / "raw" / "Kilauea_training_data.mat"
    if not mat.exists():
        raise FileNotFoundError("run tk001 acquire first")

    cycles, adapter = load_training_cycles(mat, train_n=ntrain, n_cycles=proto["split"]["n_cycles"])
    if len(cycles) != ntrain:
        raise ValueError(f"training boundary violation: expected {ntrain}, got {len(cycles)}")

    joint = fit_signal(cycles, DEFORMATION, proto)
    single_name, single, single_scores = choose_best_single_sensor(cycles, proto, sensors=DEFORMATION)
    warning = proto["warning"]
    joint_cal = calibrate_threshold(_rows(cycles, joint, "terrynce_joint_load_relief", proto), warning["target_horizon_hours"], warning["training_false_positive_rate_cap"])
    single_cal = calibrate_threshold(_rows(cycles, single, "best_single_sensor", proto), warning["target_horizon_hours"], warning["training_false_positive_rate_cap"])

    # History-only previous-cycle warning calibration, cycles 2..29.
    prev_rows = []
    for i, c in enumerate(cycles):
        if i == 0:
            continue
        for t in decision_times(c, proto):
            prev_rows.append(PredictionRow(c.cycle_id, "previous_cycle_timing", t, c.duration_hours, cycles[i-1].duration_hours))
    prev_cal = calibrate_threshold(prev_rows, warning["target_horizon_hours"], warning["training_false_positive_rate_cap"])

    src = Path(__file__).with_name("realdata.py")
    receipt = {
        "experiment_id": proto["experiment_id"],
        "stage": "FROZEN_TRAINING_CALIBRATION",
        "status": "PASS",
        "protocol_sha256": protocol_sha256(root),
        "adapter_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "split": {"training_cycles": [1, ntrain], "holdout_cycles": [ntrain + 1, proto["split"]["n_cycles"]]},
        "adapter": asdict(adapter),
        "training_duration_hours": [float(c.duration_hours) for c in cycles],
        "joint_fit": _json_fit(joint),
        "best_single_sensor": {"name": single_name, "training_checkpoint_mae": single_scores, "fit": _json_fit(single)},
        "warning_thresholds": {
            "previous_cycle_timing": prev_cal,
            "best_single_sensor": single_cal,
            "terrynce_joint_load_relief": joint_cal,
        },
        "excluded_from_terrynce_signal": ["seismicity"],
        "holdout_used_for_fit_or_threshold_selection": False,
        "boundary": "All fitted signs, scales, regression coefficients, sensor choice, and warning thresholds are now frozen. Any change requires a new experiment ID before cycles 30-39 are scored.",
    }
    art = root / "artifacts"
    art.mkdir(exist_ok=True)
    out = art / "frozen_calibration_receipt.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    (art / "frozen_calibration_receipt.sha256").write_text(hashlib.sha256(out.read_bytes()).hexdigest() + "  frozen_calibration_receipt.json\n")
    return receipt
