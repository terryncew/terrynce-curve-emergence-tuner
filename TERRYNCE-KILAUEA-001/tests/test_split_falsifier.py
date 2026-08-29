from terrynce_kilauea.synthetic import make_fixture
from terrynce_kilauea.canonical import load_csv

def test_cycle_order_is_file_order(tmp_path):
    p=tmp_path/'x.csv'
    make_fixture(p)
    c=load_csv(p)
    assert [x.cycle_id for x in c[:3]] == ['01','02','03']
    assert [x.cycle_id for x in c[-2:]] == ['38','39']
