from pathlib import Path
from terrynce_kilauea.protocol import load_protocol

def test_holdout_replay_keeps_final_verdict_withheld_until_gnn():
    text = (Path(__file__).parents[1] / "src/terrynce_kilauea/frozen_replay.py").read_text()
    assert "WITHHELD_PENDING_PUBLISHED_GNN" in text
    assert "PENDING_REPRODUCTION" in text

def test_protocol_remains_29_10_chronological():
    p = load_protocol()
    assert p["split"]["n_cycles"] == 39
    assert p["split"]["train_cycles"] == 29
    assert p["split"]["test_cycles"] == 10
    assert p["split"]["ordering"] == "chronological"

def test_holdout_replay_cannot_refit():
    text = (Path(__file__).parents[1] / "src/terrynce_kilauea/frozen_replay.py").read_text()
    assert "fit_signal(" not in text
    assert "choose_best_single_sensor(" not in text
    assert "calibrate_threshold(" not in text
