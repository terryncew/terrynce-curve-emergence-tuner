# TERRYNCE-PERCOLATION-001

A known-answer falsification test for the Terrynce Curve.

Percolation already has established critical points. This experiment asks whether a frozen Terrynce load–relief–agreement construction can recover those boundaries without being handed them, then checks whether the result contains anything beyond standard giant-component, susceptibility and spanning observables.

The experiment is intentionally allowed to lose. If the Terrynce score is effectively a renamed standard observable, the correct output is `REDUCES_TO_STANDARD_OBSERVABLE`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

tp001 --output artifacts
```

A faster smoke run:

```bash
tp001 --output artifacts-smoke --replicas 8 --sizes 12,16,20
```

Outputs are `raw.csv`, `summary.json`, and `receipt.json`. The receipt binds the result to the frozen `PREREGISTRATION.md` hash.

## Scientific boundary

A positive result does not show that percolation proves the Terrynce Curve, or that the Terrynce Curve is universal. It only earns a second transfer experiment. A negative result narrows the theory by showing that this formulation adds no measurable value beyond established critical-transition machinery.
