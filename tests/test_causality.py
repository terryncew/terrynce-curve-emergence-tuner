import numpy as np
from terrynce_kilauea.canonical import Cycle
from terrynce_kilauea.protocol import load_protocol
from terrynce_kilauea.signal import fit_signal, predict_duration


def make_cycles(n=29):
    out=[]
    for i in range(n):
        dur=28+i*0.1
        t=np.arange(0,dur-0.5,0.1)
        x=1-np.exp(-t/6)
        out.append(Cycle(str(i),t,dur,{"tilt":x.copy(),"gps":0.8*x.copy()}))
    return out


def test_future_samples_do_not_change_current_prediction():
    p=load_protocol()
    train=make_cycles()
    fit=fit_signal(train,["tilt","gps"],p)
    c=train[-1]
    t0=12.0
    pred1,_=predict_duration(c,t0,fit)
    sensors={k:v.copy() for k,v in c.sensors.items()}
    future=c.time_hours>t0
    for v in sensors.values():
        v[future]+=10000
    c2=Cycle(c.cycle_id,c.time_hours,c.duration_hours,sensors)
    pred2,_=predict_duration(c2,t0,fit)
    assert np.isclose(pred1,pred2)
