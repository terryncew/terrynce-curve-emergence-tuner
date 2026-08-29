# TERRYNCE-KILAUEA-001

A fail-closed, chronological replay harness for the final 39 Kīlauea 2018 summit-collapse cycles.

The first gate is data provenance and leakage, not model fitting. The public release contains a ~559.6 MB MATLAB archive plus the authors' GNN training/figure scripts. The published study uses the first 29 cycles for training and the last 10 for validation, with GPS, tilt and seismicity inputs. This repo freezes that same 29/10 chronological split.

## Fast path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

tk001 acquire
tk001 preflight
```

`preflight` writes:

- `artifacts/receipts.json` — hashes and source receipts
- `artifacts/schema_inventory.json` — every MATLAB/HDF5 variable, shape and dtype
- `artifacts/schema_candidates.json` — likely cycle/sensor/time/duration fields
- `artifacts/author_code_scan.json` — split/normalization/leakage-oriented scan of released code
- `artifacts/preflight_report.json` — PASS / BLOCKED with reasons
- `artifacts/protocol_lock.json` — SHA-256 of the frozen protocol

The command fails closed if the archive hash does not match the pinned Zenodo MD5 or if a plausible 39-cycle axis cannot be found.

## Why there is a preflight gate

The dataset is large and MATLAB layouts can hide cell references, transposed cycle axes, or preprocessing outputs. Guessing the schema would be exactly the kind of quiet leakage this experiment is supposed to rule out. The harness inventories first, then the canonical adapter is locked against that receipt before any holdout replay.

## Canonical replay format

The experiment runner consumes a CSV with these columns:

```text
cycle_id,time_hours,duration_hours,<sensor columns...>
```

Rows are chronological inside each cycle. `cycle_id` must have exactly 39 unique values in chronological order. `duration_hours` is evaluation truth only; feature code never receives it. Sensor columns are numeric; the intended deformation set is five GPS radial series plus tilt. Seismicity can be carried for the published baseline but is excluded from the frozen Terrynce signal unless the preregistration is versioned before holdout access.

After the preflight identifies the source fields, create `data/processed/kilauea39.csv`, then:

```bash
tk001 validate data/processed/kilauea39.csv
tk001 replay data/processed/kilauea39.csv
```

To include the published GNN, provide a CSV of causal duration predictions:

```text
cycle_id,time_hours,predicted_duration_hours
```

and run:

```bash
tk001 replay data/processed/kilauea39.csv --gnn data/processed/gnn_predictions.csv
```

Without the GNN file, the report marks that baseline `UNAVAILABLE`; it never fabricates a number from the paper table.

## Scientific boundary

A win here means: on cycles 30–39, the frozen joint signal adds forecast value beyond the baselines under matched false-alarm constraints. It does not establish a universal transition law.
