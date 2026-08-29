from terrynce_kilauea.canonical import load_csv, validate_cycles
from terrynce_kilauea.synthetic import make_fixture

def test_synthetic_validates(tmp_path):
    p = tmp_path / "x.csv"
    make_fixture(p)
    result = validate_cycles(load_csv(p), 39)
    assert result["status"] == "PASS"
    assert len(result["sensors"]) == 6
