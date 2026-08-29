from terrynce_kilauea.synthetic import make_fixture
from terrynce_kilauea.replay import replay


def test_replay_runs_and_keeps_gnn_unavailable(tmp_path):
    data=tmp_path/'synthetic39.csv'
    make_fixture(data)
    report=replay(data)
    assert report['data']['status']=='PASS'
    assert report['models']['published_gnn']['status']=='UNAVAILABLE'
    assert report['models']['terrynce_joint_load_relief']['status']=='AVAILABLE'
