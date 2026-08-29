from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat


def _shape(x: Any) -> list[int]:
    try:
        return list(np.asarray(x).shape)
    except Exception:
        return []


def probe_author_schema(mat_path: Path, artifacts: Path, n_cycles: int = 39) -> dict:
    """Probe the released MATLAB cell-array layout without flattening the data.

    The author's released training script indexes:
      X_l_s[0][i][0,:,:,:]
      Y_l_s[0][i][:,0]
      Max_t[i]
    and fixes train=np.arange(29), validation=np.arange(29,39).

    This probe establishes whether the downloaded archive actually supports that
    layout. It records shapes/counts only; it does not expose holdout values.
    """
    z = loadmat(
        mat_path,
        variable_names=["X_l", "Y_l", "Trunc_l", "Max_t"],
        squeeze_me=False,
        struct_as_record=False,
    )
    missing = [k for k in ("X_l", "Y_l", "Trunc_l", "Max_t") if k not in z]
    report: dict[str, Any] = {"missing": missing}
    if missing:
        report["status"] = "FAIL"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "author_schema_probe.json").write_text(json.dumps(report, indent=2) + "\n")
        return report

    Xc = z["X_l"]
    Yc = z["Y_l"]
    max_t = np.asarray(z["Max_t"]).reshape(-1)
    trunc = np.asarray(z["Trunc_l"]).reshape(-1)

    n_series = int(Xc.shape[1]) if Xc.ndim == 2 and Xc.shape[0] == 1 else int(Xc.size)
    x_cells = [Xc.reshape(-1)[i] for i in range(Xc.size)]
    y_cells = [Yc.reshape(-1)[i] for i in range(Yc.size)]

    x_shapes = [_shape(x) for x in x_cells]
    y_shapes = [_shape(y) for y in y_cells]

    # Author code uses X_l_s[0][i][0,:,:,:] and then indexes cycle on the
    # last dimension; Y_l_s[0][i][:,0] has one row per collapse cycle.
    x_cycle_ok = [bool(s and s[-1] == n_cycles) for s in x_shapes]
    y_cycle_ok = [bool(s and s[0] == n_cycles) for s in y_shapes]

    channel_counts = []
    for s in x_shapes:
        # After [0,:,:,:], expected layout is time x channel x cycle.
        # Original cell therefore normally has >=4 dims and channel axis -2.
        channel_counts.append(int(s[-2]) if len(s) >= 3 else None)

    report.update({
        "status": "PASS" if (x_cells and y_cells and all(x_cycle_ok) and all(y_cycle_ok)) else "FAIL",
        "n_series": n_series,
        "x_cell_count": len(x_cells),
        "y_cell_count": len(y_cells),
        "x_shapes": x_shapes,
        "y_shapes": y_shapes,
        "x_all_last_axis_39": bool(x_cycle_ok and all(x_cycle_ok)),
        "y_all_first_axis_39": bool(y_cycle_ok and all(y_cycle_ok)),
        "channel_counts": channel_counts,
        "max_t_len": int(max_t.size),
        "trunc_l_len": int(trunc.size),
        "author_channel_map": {
            "0-4": "GPS stations (5)",
            "5": "tilt",
            "6": "cumulative seismicity counts",
        },
        "author_split": {"train": [0, 28], "holdout": [29, 38], "n_train": 29, "n_holdout": 10},
        "author_norm_scale": [80.0, 80.0, 80.0, 80.0, 80.0, 20.0, 300.0],
        "holdout_values_read_or_exported": False,
    })

    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "author_schema_probe.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
