import numpy as np
from pathlib import Path
from scipy.io import savemat

from terrynce_kilauea.realdata import load_training_cycles


def _fixture(path: Path, holdout_bump: float = 0.0):
    n_t, n_c = 1400, 39
    x = np.zeros((1, n_t, 7, n_c), float)
    for c in range(n_c):
        t = np.arange(n_t) / 60.0
        for j in range(7):
            x[0, :, j, c] = (j + 1) * (1.0 - np.exp(-t / (2 + 0.05*c)))
    if holdout_bump:
        x[..., 29:] += holdout_bump
    y = np.linspace(0.9, 2.0, n_c)[:, None]
    if holdout_bump:
        y[29:] += holdout_bump
    X_l = np.empty((1,1), dtype=object); X_l[0,0] = x
    Y_l = np.empty((1,1), dtype=object); Y_l[0,0] = y
    savemat(path, {"X_l": X_l, "Y_l": Y_l})


def test_training_adapter_uses_exactly_first_29(tmp_path):
    p = tmp_path / 'a.mat'; _fixture(p)
    cycles, rec = load_training_cycles(p)
    assert len(cycles) == 29
    assert rec.n_cycles_extracted == 29
    assert abs(cycles[0].duration_hours - 21.6) < 1e-9


def test_holdout_mutation_cannot_change_extracted_training(tmp_path):
    a = tmp_path/'a.mat'; b = tmp_path/'b.mat'
    _fixture(a, 0.0); _fixture(b, 100.0)
    ca, _ = load_training_cycles(a); cb, _ = load_training_cycles(b)
    for x, y in zip(ca, cb):
        assert x.duration_hours == y.duration_hours
        for s in x.sensors:
            np.testing.assert_allclose(x.sensors[s], y.sensors[s])
