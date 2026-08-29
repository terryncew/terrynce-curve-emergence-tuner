from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import h5py
import numpy as np


def _scalar_attr(v: Any) -> Any:
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, np.ndarray):
        if v.size <= 16:
            return [_scalar_attr(x) for x in v.tolist()]
        return {"shape": list(v.shape), "dtype": str(v.dtype)}
    if isinstance(v, np.generic):
        return v.item()
    return v


def _sample_stats(ds: h5py.Dataset) -> dict:
    if ds.size == 0 or ds.dtype.kind not in "iufb":
        return {}
    try:
        if ds.size <= 100_000:
            x = np.asarray(ds[...]).astype(float, copy=False).ravel()
        else:
            sl = tuple(slice(0, min(n, 16)) for n in ds.shape)
            x = np.asarray(ds[sl]).astype(float, copy=False).ravel()
        x = x[np.isfinite(x)]
        if x.size == 0:
            return {"finite_samples": 0}
        return {
            "finite_samples": int(x.size),
            "sample_min": float(np.min(x)),
            "sample_max": float(np.max(x)),
            "sample_mean": float(np.mean(x)),
        }
    except Exception as e:
        return {"sample_error": type(e).__name__}


def inventory_hdf5(path: Path) -> list[dict]:
    rows: list[dict] = []
    with h5py.File(path, "r") as f:
        def visit(name: str, obj: h5py.Group | h5py.Dataset) -> None:
            row = {
                "path": "/" + name,
                "kind": "dataset" if isinstance(obj, h5py.Dataset) else "group",
                "attrs": {str(k): _scalar_attr(v) for k, v in obj.attrs.items()},
            }
            if isinstance(obj, h5py.Dataset):
                row.update({"shape": list(obj.shape), "dtype": str(obj.dtype), "size": int(obj.size)})
                row.update(_sample_stats(obj))
            rows.append(row)
        f.visititems(visit)
    return rows


def inventory_legacy_mat(path: Path) -> list[dict]:
    from scipy.io import whosmat
    return [
        {"path": "/" + name, "kind": "mat_variable", "shape": list(shape), "dtype": cls}
        for name, shape, cls in whosmat(path)
    ]


def inventory_mat(path: Path) -> tuple[str, list[dict]]:
    try:
        with h5py.File(path, "r"):
            pass
        return "matlab_v7.3_hdf5", inventory_hdf5(path)
    except OSError:
        return "legacy_mat", inventory_legacy_mat(path)


def candidates(rows: list[dict], n_cycles: int = 39) -> dict:
    pats = {
        "gps": re.compile(r"gps|gnss|ahup|byrl|crim|outl|uwev", re.I),
        "tilt": re.compile(r"tilt", re.I),
        "seismicity": re.compile(r"seis|quake|earth|count|catalog", re.I),
        "time": re.compile(r"time|hour|sec|date", re.I),
        "duration": re.compile(r"duration|repeat|recurr|failure|collapse|event", re.I),
    }
    out = {k: [] for k in pats}
    out["cycle_axis"] = []
    for row in rows:
        p = row.get("path", "")
        shape = row.get("shape", [])
        for k, pat in pats.items():
            if pat.search(p):
                out[k].append({"path": p, "shape": shape, "dtype": row.get("dtype")})
        if n_cycles in shape:
            out["cycle_axis"].append({"path": p, "shape": shape, "dtype": row.get("dtype")})
    return out


def write_inventory(path: Path, artifacts: Path, n_cycles: int = 39) -> dict:
    fmt, rows = inventory_mat(path)
    cands = candidates(rows, n_cycles=n_cycles)
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "schema_inventory.json").write_text(json.dumps({"format": fmt, "variables": rows}, indent=2))
    (artifacts / "schema_candidates.json").write_text(json.dumps(cands, indent=2))
    return {"format": fmt, "variables": len(rows), "candidates": cands}
