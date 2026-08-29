# Build status

Implemented now:

- pinned Zenodo v2 record and published MD5 receipts;
- streaming acquisition with hash verification;
- recursive MATLAB v7.3 / legacy MAT inventory;
- 39-cycle schema-candidate detection;
- released-author-code scan focused on split and normalization review;
- immutable 29/10 chronological protocol hash;
- canonical data validator;
- causal joint load–relief feature and train-only calibration;
- previous-cycle and best-single-sensor baselines;
- external published-GNN prediction interface;
- matched training false-positive-rate warning thresholding;
- 12 h / 24 h timing metrics, false alarms, warning lead, and abstention/miss metrics;
- synthetic end-to-end tests and CI.

Blocked by evidence, not code: this build environment could read the Zenodo record and paper but could not fetch the 559.6 MB payload from Zenodo. Therefore no claim is made that the source archive has been locally hashed, that its internal field mapping is known, or that the experiment has run on the real Kīlauea data. `tk001 preflight` is designed to produce exactly that receipt on a machine with normal Zenodo access and to stop before holdout replay if the archive/schema does not match.

## GitHub Actions integration

The repository-root workflow is `.github/workflows/terrynce-kilauea-001.yml` and appears in Actions as `TERRYNCE-KILAUEA-001`. It runs only when this experiment or its workflow changes, and also supports manual dispatch.

## Real-data preflight workflow

Run **TERRYNCE-KILAUEA-001 Real Data Preflight** manually in GitHub Actions. It acquires and verifies the published archive on the runner, performs schema/leakage preflight, and uploads only receipt JSON artifacts. A green workflow means acquisition/integrity hard checks cleared; any `REVIEW` item still must be resolved before held-out scoring.
