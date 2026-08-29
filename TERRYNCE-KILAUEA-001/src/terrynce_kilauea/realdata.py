from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
from scipy.io import loadmat

from .canonical import Cycle

CHANNEL_NAMES = ["gps_0", "gps_1", "gps_2", "gps_3", "gps_4", "tilt", "seismicity"]
SAMPLE_INTERVAL_HOURS = 1.0 / 60.0  # paper: input data sampled at 1/60 Hz


@dataclass(frozen=True)
class AdapterReceipt:
    x_cell_index: int
    x_shape: list[int]
    y_cell_index: int
    y_shape: list[int]
    target_unit: str
    target_multiplier_to_hours: float
    sample_interval_hours: float
    n_cycles_extracted: int
    channel_names: list[str]


def _cells(x: Any) -> list[np.ndarray]:
    a = np.asarray(x, dtype=object)
    return [np.asarray(v) for v in a.reshape(-1)]


def _select_x_cell(x_cells: list[np.ndarray], n_cycles: int) -> tuple[int, np.ndarray]:
    candidates: list[tuple[int, int, np.ndarray]] = []
    for i, x in enumerate(x_cells):
        s = x.shape
        if len(s) >= 3 and s[-1] == n_cycles and s[-2] >= 7:
            # Prefer the cell with the longest temporal axis; leading singleton dims are harmless.
            time_len = int(np.prod(s[:-2]))
            candidates.append((time_len, i, x))
    if not candidates:
        raise ValueError("no X_l cell has [..., >=7 channels, 39 cycles] layout")
    _, i, x = max(candidates, key=lambda z: z[0])
    return i, x


def _select_y_cell(y_cells: list[np.ndarray], n_cycles: int) -> tuple[int, np.ndarray]:
    for i, y in enumerate(y_cells):
        s = y.shape
        if s and s[0] == n_cycles:
            return i, y
    raise ValueError("no Y_l cell has first axis equal to 39 cycles")


def _target_hours(y: np.ndarray, train_n: int) -> tuple[np.ndarray, str, float]:
    vals = np.asarray(y[:, 0] if y.ndim >= 2 else y, float).reshape(-1)
    train = vals[:train_n]
    med = float(np.nanmedian(train))
    # Source-backed range is ~0.84--2.23 days. Unit choice is derived from training only.
    if 0.5 <= med <= 3.0:
        return vals * 24.0, "days", 24.0
    if 12.0 <= med <= 72.0:
        return vals, "hours", 1.0
    raise ValueError(f"cannot infer released target unit from training values; training median={med}")


def load_training_cycles(mat_path: Path, train_n: int = 29, n_cycles: int = 39) -> tuple[list[Cycle], AdapterReceipt]:
    z = loadmat(mat_path, variable_names=["X_l", "Y_l"], squeeze_me=False, struct_as_record=False)
    if "X_l" not in z or "Y_l" not in z:
        raise ValueError("released MAT file missing X_l or Y_l")
    xi, x = _select_x_cell(_cells(z["X_l"]), n_cycles)
    yi, y = _select_y_cell(_cells(z["Y_l"]), n_cycles)
    durations, unit, mult = _target_hours(y, train_n)

    # Collapse all leading axes into time. Released indexing is X_l_s[0][i][0,:,:,:],
    # with channel at -2 and cycle at -1. This accepts the leading singleton explicitly.
    arr = np.asarray(x, float)
    arr = arr.reshape((-1, arr.shape[-2], arr.shape[-1]))
    if arr.shape[1] < 7 or arr.shape[2] != n_cycles:
        raise ValueError(f"unexpected released X layout after reshape: {arr.shape}")

    cycles: list[Cycle] = []
    for i in range(train_n):
        dur = float(durations[i])
        if not np.isfinite(dur) or dur <= 0:
            raise ValueError(f"cycle {i+1}: invalid training duration")
        n = min(arr.shape[0], int(np.floor(dur / SAMPLE_INTERVAL_HOURS)) + 1)
        if n < 5:
            raise ValueError(f"cycle {i+1}: insufficient causal samples")
        data = arr[:n, :7, i]
        if not np.isfinite(data).all():
            raise ValueError(f"cycle {i+1}: non-finite training sensor values")
        t = np.arange(n, dtype=float) * SAMPLE_INTERVAL_HOURS
        cycles.append(Cycle(
            cycle_id=f"cycle_{i+1:02d}",
            time_hours=t,
            duration_hours=dur,
            sensors={name: data[:, j].copy() for j, name in enumerate(CHANNEL_NAMES)},
        ))

    receipt = AdapterReceipt(
        x_cell_index=xi,
        x_shape=list(np.asarray(x).shape),
        y_cell_index=yi,
        y_shape=list(np.asarray(y).shape),
        target_unit=unit,
        target_multiplier_to_hours=mult,
        sample_interval_hours=SAMPLE_INTERVAL_HOURS,
        n_cycles_extracted=len(cycles),
        channel_names=CHANNEL_NAMES.copy(),
    )
    return cycles, receipt

def load_all_cycles(mat_path: Path, train_n: int = 29, n_cycles: int = 39) -> tuple[list[Cycle], AdapterReceipt]:
    """Load all 39 chronological cycles after calibration has been frozen.

    Target-unit inference remains training-only: only the first `train_n` targets
    determine the days-vs-hours multiplier.
    """
    z = loadmat(mat_path, variable_names=["X_l", "Y_l"], squeeze_me=False, struct_as_record=False)
    if "X_l" not in z or "Y_l" not in z:
        raise ValueError("released MAT file missing X_l or Y_l")
    xi, x = _select_x_cell(_cells(z["X_l"]), n_cycles)
    yi, y = _select_y_cell(_cells(z["Y_l"]), n_cycles)
    durations, unit, mult = _target_hours(y, train_n)

    arr = np.asarray(x, float)
    arr = arr.reshape((-1, arr.shape[-2], arr.shape[-1]))
    if arr.shape[1] < 7 or arr.shape[2] != n_cycles:
        raise ValueError(f"unexpected released X layout after reshape: {arr.shape}")

    cycles: list[Cycle] = []
    for i in range(n_cycles):
        dur = float(durations[i])
        if not np.isfinite(dur) or dur <= 0:
            raise ValueError(f"cycle {i+1}: invalid duration")
        n = min(arr.shape[0], int(np.floor(dur / SAMPLE_INTERVAL_HOURS)) + 1)
        if n < 5:
            raise ValueError(f"cycle {i+1}: insufficient causal samples")
        data = arr[:n, :7, i]
        if not np.isfinite(data).all():
            raise ValueError(f"cycle {i+1}: non-finite sensor values")
        t = np.arange(n, dtype=float) * SAMPLE_INTERVAL_HOURS
        cycles.append(Cycle(
            cycle_id=f"cycle_{i+1:02d}",
            time_hours=t,
            duration_hours=dur,
            sensors={name: data[:, j].copy() for j, name in enumerate(CHANNEL_NAMES)},
        ))

    receipt = AdapterReceipt(
        x_cell_index=xi,
        x_shape=list(np.asarray(x).shape),
        y_cell_index=yi,
        y_shape=list(np.asarray(y).shape),
        target_unit=unit,
        target_multiplier_to_hours=mult,
        sample_interval_hours=SAMPLE_INTERVAL_HOURS,
        n_cycles_extracted=len(cycles),
        channel_names=CHANNEL_NAMES.copy(),
    )
    return cycles, receipt

