from terrynce_kilauea.protocol import load_protocol, protocol_sha256

def test_split_is_frozen_29_10():
    p = load_protocol()
    assert p["split"] == {"n_cycles": 39, "train_cycles": 29, "test_cycles": 10, "ordering": "chronological"}
    assert len(protocol_sha256()) == 64
