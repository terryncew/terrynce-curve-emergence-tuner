from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .canonical import Cycle


EPS = 1e-9


def _interp(t: np.ndarray, x: np.ndarray, q: float) -> float:
    if q < t[0] or q > t[-1]:
        return float("nan")
    return float(np.interp(q, t, x))


def causal_slope(t: np.ndarray, x: np.ndarray, end_h: float, width_h: float) -> float:
    mask = (t <= end_h + 1e-12) & (t >= end_h - width_h - 1e-12)
    tt = t[mask]
    xx = x[mask]
    if len(tt) < 3:
        return float("nan")
    tt = tt - tt.mean()
    denom = float(np.dot(tt, tt))
    if denom <= EPS:
        return float("nan")
    return float(np.dot(tt, xx - xx.mean()) / denom)


@dataclass
class SignalFit:
    sensors: list[str]
    signs: dict[str, float]
    scales: dict[str, float]
    early_rates: dict[str, float]
    x_mean: np.ndarray
    x_scale: np.ndarray
    beta: np.ndarray
    ridge_lambda: float


def raw_signal(cycle: Cycle, time_h: float, fit: SignalFit) -> float:
    ps, es, agree = [], [], []
    for s in fit.sensors:
        x = cycle.sensors[s]
        x0 = _interp(cycle.time_hours, x, float(cycle.time_hours[0]))
        xt = _interp(cycle.time_hours, x, time_h)
        if not np.isfinite(xt):
            continue
        signed = fit.signs[s] * (xt - x0)
        p = np.clip(signed / max(fit.scales[s], EPS), 0.0, 2.0)
        slope = causal_slope(cycle.time_hours, x, time_h, width_h=1.0)
        if not np.isfinite(slope):
            continue
        e = np.clip(1.0 - abs(slope) / max(fit.early_rates[s], EPS), 0.0, 1.5)
        ps.append(p)
        es.append(e)
        agree.append(1.0 if signed >= 0 else 0.0)
    if not ps:
        return float("nan")
    L = float(np.median(ps))
    E = float(np.median(es))
    A = float(np.mean(agree))
    return L * E * A


def _decision_times(c: Cycle, start_h: float, step_h: float, stop_before_h: float) -> np.ndarray:
    end = c.duration_hours - stop_before_h
    if end < start_h:
        return np.empty(0)
    n = int(np.floor((end - start_h) / step_h)) + 1
    return start_h + np.arange(n) * step_h


def fit_signal(train: list[Cycle], sensors: list[str], protocol: dict) -> SignalFit:
    sigcfg = protocol["signal"]
    start = protocol["decision_grid"]["start_hours"]
    early0, early1 = sigcfg["early_rate_window_hours"]
    q = sigcfg["progress_scale_quantile"]
    signs, scales, early_rates = {}, {}, {}
    for s in sensors:
        end_changes, rates = [], []
        for c in train:
            x = c.sensors[s]
            t_eval = min(c.duration_hours - 1.0, float(c.time_hours[-1]))
            if t_eval <= c.time_hours[0]:
                continue
            x0 = _interp(c.time_hours, x, float(c.time_hours[0]))
            xe = _interp(c.time_hours, x, t_eval)
            if np.isfinite(xe):
                end_changes.append(xe - x0)
            for eh in (early0, (early0 + early1) / 2, early1):
                if eh <= c.duration_hours - 1.0:
                    r = causal_slope(c.time_hours, x, eh, width_h=1.0)
                    if np.isfinite(r):
                        rates.append(abs(r))
        if not end_changes:
            raise ValueError(f"cannot fit direction/scale for {s}")
        med = float(np.median(end_changes))
        signs[s] = 1.0 if med >= 0 else -1.0
        scales[s] = max(float(np.quantile(np.abs(end_changes), q)), EPS)
        early_rates[s] = max(float(np.median(rates)) if rates else EPS, EPS)

    dummy = SignalFit(sensors, signs, scales, early_rates, np.zeros(3), np.ones(3), np.zeros(4), sigcfg["ridge_lambda"])
    X, y = [], []
    step_h = protocol["decision_grid"]["step_minutes"] / 60.0
    for c in train:
        for t in _decision_times(c, start, step_h, protocol["decision_grid"]["stop_before_failure_hours"]):
            s = raw_signal(c, float(t), dummy)
            if np.isfinite(s):
                X.append([float(t), s, float(t) * s])
                y.append(c.duration_hours)
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < EPS] = 1.0
    Z = (X - mu) / sd
    D = np.column_stack([np.ones(len(Z)), Z])
    lam = float(sigcfg["ridge_lambda"])
    reg = np.eye(D.shape[1]) * lam
    reg[0, 0] = 0.0
    beta = np.linalg.solve(D.T @ D + reg, D.T @ y)
    return SignalFit(sensors, signs, scales, early_rates, mu, sd, beta, lam)


def predict_duration(cycle: Cycle, time_h: float, fit: SignalFit) -> tuple[float, float]:
    s = raw_signal(cycle, time_h, fit)
    if not np.isfinite(s):
        return float("nan"), float("nan")
    x = np.asarray([time_h, s, time_h * s], float)
    z = (x - fit.x_mean) / fit.x_scale
    pred = float(np.dot(np.r_[1.0, z], fit.beta))
    return pred, s
