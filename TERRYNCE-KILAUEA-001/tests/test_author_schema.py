from pathlib import Path
import numpy as np
from scipy.io import savemat

from terrynce_kilauea.author_schema import probe_author_schema


def test_author_cell_schema_detects_39_cycles(tmp_path: Path):
    X = np.empty((1, 2), dtype=object)
    Y = np.empty((1, 2), dtype=object)
    for i, nt in enumerate((20, 30)):
        X[0, i] = np.zeros((1, nt, 7, 39), dtype=np.float32)
        Y[0, i] = np.arange(39, dtype=float).reshape(39, 1)
    p = tmp_path / "k.mat"
    savemat(p, {"X_l": X, "Y_l": Y, "Trunc_l": np.array([[1, 2]]), "Max_t": np.array([[1, 2]])})
    r = probe_author_schema(p, tmp_path / "artifacts", 39)
    assert r["status"] == "PASS"
    assert r["x_all_last_axis_39"] is True
    assert r["y_all_first_axis_39"] is True
    assert r["channel_counts"] == [7, 7]
