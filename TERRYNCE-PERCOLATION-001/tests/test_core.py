from pathlib import Path
import math
from terrynce_percolation.core import KNOWN_PC, add_terrynce_score, aggregate, estimate_pc, pearson
from terrynce_percolation.runner import run


def test_known_critical_points_are_explicit():
    assert KNOWN_PC["square_bond"] == 0.5
    assert abs(KNOWN_PC["square_site"] - 0.59274605079210) < 1e-12
    assert KNOWN_PC["triangular_site"] == 0.5


def test_aggregate_is_deterministic():
    a = aggregate("square_bond", 8, 0.5, 4, 123)
    b = aggregate("square_bond", 8, 0.5, 4, 123)
    assert a == b


def test_terrynce_score_does_not_require_known_pc():
    rows = [aggregate("square_bond", 8, p, 3, 1000 + i * 10) for i, p in enumerate([0.4, 0.5, 0.6])]
    scored = add_terrynce_score(rows)
    middle = [r for r in scored if r["p"] == 0.5][0]
    assert math.isfinite(middle["terrynce_gradient"])
    assert 0.0 <= middle["terrynce_score"] <= 1.0


def test_smoke_pc_is_in_transition_region():
    ps = [0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65]
    rows = [aggregate("square_bond", 14, p, 12, 9000 + i * 100) for i, p in enumerate(ps)]
    scored = add_terrynce_score(rows)
    estimate = estimate_pc(scored, "square_bond", 14, "terrynce_gradient")
    assert 0.35 < estimate < 0.65


def test_pearson_identity():
    assert pearson([1, 2, 3], [2, 4, 6]) > 0.999999


def test_runner_writes_bound_receipts(tmp_path: Path):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen\n")
    summary = run(tmp_path / "out", protocol, replicas=3, sizes=[8], families=["square_bond"], grid=[0.4, 0.5, 0.6])
    assert (tmp_path / "out" / "raw.csv").exists()
    assert (tmp_path / "out" / "summary.json").exists()
    assert (tmp_path / "out" / "receipt.json").exists()
    assert summary["protocol_sha256"]
    assert summary["disposition"] in {"ADDITIVE_SIGNAL_CANDIDATE", "REDUCES_TO_STANDARD_OBSERVABLE", "NO_ADDITIVE_VALUE"}
