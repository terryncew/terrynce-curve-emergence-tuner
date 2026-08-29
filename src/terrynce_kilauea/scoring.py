from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np


@dataclass
class PredictionRow:
    cycle_id: str
    model: str
    time_hours: float
    true_duration_hours: float
    predicted_duration_hours: float

    @property
    def true_remaining(self) -> float:
        return self.true_duration_hours - self.time_hours

    @property
    def pred_remaining(self) -> float:
        return self.predicted_duration_hours - self.time_hours

    @property
    def score(self) -> float:
        return -self.pred_remaining


def calibrate_threshold(rows: list[PredictionRow], horizon_h: float, fpr_cap: float) -> dict:
    vals = [(r.score, r.true_remaining <= horizon_h and r.true_remaining > 0) for r in rows if np.isfinite(r.score) and r.true_remaining > 0]
    if not vals:
        return {"threshold": float("inf"), "train_fpr": 0.0, "train_tpr": 0.0}
    scores = np.asarray([v[0] for v in vals])
    labels = np.asarray([v[1] for v in vals], bool)
    candidates = np.unique(scores)
    best = None
    for th in candidates:
        pred = scores >= th
        neg = ~labels
        pos = labels
        fpr = float(np.mean(pred[neg])) if np.any(neg) else 0.0
        tpr = float(np.mean(pred[pos])) if np.any(pos) else 0.0
        if fpr <= fpr_cap + 1e-12:
            key = (tpr, -fpr, -float(th))
            if best is None or key > best[0]:
                best = (key, float(th), fpr, tpr)
    if best is None:
        return {"threshold": float("inf"), "train_fpr": 0.0, "train_tpr": 0.0}
    return {"threshold": best[1], "train_fpr": best[2], "train_tpr": best[3]}


def point_metrics(rows: list[PredictionRow], checkpoints: list[float], tol_h: float = 0.13) -> dict:
    out = {}
    for cp in checkpoints:
        rr = [r for r in rows if abs(r.time_hours - cp) <= tol_h and np.isfinite(r.predicted_duration_hours)]
        e = np.asarray([r.predicted_duration_hours - r.true_duration_hours for r in rr], float)
        out[str(cp)] = {
            "n": int(len(e)),
            "mae_hours": float(np.mean(np.abs(e))) if len(e) else None,
            "rmse_hours": float(np.sqrt(np.mean(e**2))) if len(e) else None,
            "bias_hours": float(np.mean(e)) if len(e) else None,
        }
    return out


def warning_metrics(rows: list[PredictionRow], threshold: float, horizon_h: float, persistence_steps: int) -> dict:
    by_cycle: dict[str, list[PredictionRow]] = {}
    for r in rows:
        by_cycle.setdefault(r.cycle_id, []).append(r)
    false_epoch, neg_epoch, pos_epoch, hit_epoch = 0, 0, 0, 0
    leads = []
    misses = 0
    for cid, rr in by_cycle.items():
        rr.sort(key=lambda r: r.time_hours)
        streak = 0
        first_true_lead = None
        for r in rr:
            if not np.isfinite(r.score) or r.true_remaining <= 0:
                streak = 0
                continue
            truth = r.true_remaining <= horizon_h
            alert = r.score >= threshold
            if truth:
                pos_epoch += 1
                if alert:
                    hit_epoch += 1
            else:
                neg_epoch += 1
                if alert:
                    false_epoch += 1
            streak = streak + 1 if alert else 0
            if streak >= persistence_steps and truth and first_true_lead is None:
                first_true_lead = r.true_remaining
        if first_true_lead is None:
            misses += 1
        else:
            leads.append(first_true_lead)
    return {
        "false_positive_rate": false_epoch / neg_epoch if neg_epoch else 0.0,
        "epoch_detection_rate": hit_epoch / pos_epoch if pos_epoch else 0.0,
        "cycle_abstention_miss_rate": misses / len(by_cycle) if by_cycle else None,
        "median_valid_warning_lead_hours": float(np.median(leads)) if leads else None,
        "n_cycles": len(by_cycle),
    }
