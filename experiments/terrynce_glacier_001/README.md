# TERRYNCE-GLACIER-001

This experiment asks one bounded question:

> Does fast upstream motion combined with a failure of terminus relief warn of
> glacier detachment earlier than velocity alone or a prospective power-law
> forecast, at the same observed false-alarm burden?

It does **not** revive the Bridge Equation, predict the 2026 Nepal disaster, or
claim a universal tipping signal. Bukadaban East and West define a mechanical
design pair. Other glaciers must decide whether the feature transfers.

## Current disposition

`PUBLIC_DATA_INSUFFICIENT_FOR_FROZEN_HEADLINE_TEST`

The open Zenodo displacement archive is genuine and useful, but it cannot yet
run the preregistered comparison:

- Bukadaban East ends on 2022-10-16, 16 days before detachment. The paper's
  26 m/day and 46 m/day final observations are absent.
- The archive contains no frozen upstream/terminus role labels or terminus
  position series. Inferring those masks after seeing the outcome would grade
  our own homework.
- Bukadaban West contributes about 1.14 glacier-years of control exposure;
  the frozen calibration requires at least five.
- The final-prefix acquisition cadence fails the preregistered critical
  slowing down sampling gate.

The data gap is a result, not a request to interpolate harder.

## Reproduce the receipt

```bash
python experiments/terrynce_glacier_001/run_feasibility.py \
  --archive /path/to/disp.zip \
  --output /tmp/PUBLIC_DATA_FEASIBILITY.json

python experiments/terrynce_glacier_001/verify_feasibility.py \
  --archive /path/to/disp.zip \
  --result /tmp/PUBLIC_DATA_FEASIBILITY.json
```

The runner is standard-library only. It checks the source hash, ZIP safety,
file schema, acquisition coverage, control exposure, and the CSD density gate.
It exits successfully when the honest finding is `INSUFFICIENT`; use
`--require-ready` only when a downstream job truly requires a runnable
headline comparison.

## What unlocks the frozen run

All four inputs must be pinned before any threshold is fit:

1. Author-derived final Bukadaban East observations through 2022-11-01.
2. A published or author-supplied spatial role map for upstream and terminus
   measurements, plus terminus-position observations.
3. A frozen non-detaching control roster totaling at least five glacier-years.
4. A separately sourced Chamoli series for the hostile scope test.

Until then, no warning-performance number is earned.

## External derived-data intake

The next stage is implemented under [`author_intake/`](author_intake/). It
publishes the missing-data specification and a fail-closed validator for any
independently supplied bundle. Raw PlanetScope imagery is outside the contract.
A bundle becomes eligible only when its file hashes, provenance, final East
interval, frozen spatial roles, terminus series, five glacier-years of observed
controls, and CSD cadence all pass.
