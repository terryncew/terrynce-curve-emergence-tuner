# Terrynce Curve

**A falsifiable research program for testing early-warning signals before abrupt system transitions.**

[![TERRYNCE-GLACIER-001](https://github.com/terryncew/terrynce-curve-emergence-tuner/actions/workflows/terrynce-glacier-001.yml/badge.svg)](https://github.com/terryncew/terrynce-curve-emergence-tuner/actions/workflows/terrynce-glacier-001.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Can a system reveal that it is approaching a regime change before the break
becomes obvious? This repository turns that broad question into frozen,
hostile tests against real observations.

The current work is research, not a production safety monitor. It does not
predict glacier collapse, certify physical safety, or establish a universal
tipping-point equation.

## Current result

### TERRYNCE-GLACIER-001

**Status:** `PUBLIC_DATA_INSUFFICIENT_FOR_FROZEN_HEADLINE_TEST`

The first experiment asks whether fast upstream glacier motion combined with
a pinned terminus warns of detachment earlier than velocity alone or a
prospective power-law forecast, under the same false-alarm bound.

The public source archive verified successfully. It does not contain enough
information to run that comparison without inventing observations or defining
spatial roles after seeing the outcome:

- the Bukadaban East record ends 16 days before detachment;
- the paper's final 26 m/day and 46 m/day observations are absent;
- upstream and terminus roles are not frozen in the archive;
- the available control exposure is about 1.14 glacier-years, below the
  preregistered five-year minimum; and
- the final-prefix cadence fails the critical-slowing-down sampling gate.

No warning lead time or superiority result was calculated. The hypothesis
remains untested.

## Why keep a blocked experiment public?

Because the block is part of the evidence. The design was frozen before the
data were inspected, and the gate refused to turn an incomplete archive into a
clean-looking discovery.

The next valid transition is simple:

```text
missing observations supplied
        ↓
external bundle verifies
        ↓
frozen walk-forward comparison runs
        ↓
signal beats the baselines—or it does not
```

Until the first step happens, adding another detector would only make the code
more confident than the data.

## Reproduce the public-data receipt

Download `disp.zip` from the pinned
[Zenodo record](https://doi.org/10.5281/zenodo.17754687), then run:

```bash
python experiments/terrynce_glacier_001/run_feasibility.py \
  --archive /path/to/disp.zip \
  --output /tmp/PUBLIC_DATA_FEASIBILITY.json

python experiments/terrynce_glacier_001/verify_feasibility.py \
  --archive /path/to/disp.zip \
  --result /tmp/PUBLIC_DATA_FEASIBILITY.json
```

The runner uses only Python's standard library. It verifies the source hash,
rejects unsafe ZIP paths, checks the schema, computes observed control
exposure, and applies the frozen sampling gates.

## Repository map

| Path | Purpose |
|---|---|
| [`experiments/terrynce_glacier_001/`](experiments/terrynce_glacier_001/) | Preregistration, sources, frozen receipt, and verifier |
| [`experiments/terrynce_glacier_001/author_intake/`](experiments/terrynce_glacier_001/author_intake/) | Public contract for independently supplied derived measurements |
| [`tests/`](tests/) | Contract, provenance, and public-surface tests |
| [`docs/`](docs/) | Human-readable project page and current receipt projection |

## Research rules

1. Features and thresholds are fixed before outcomes are revealed.
2. Every proposed signal competes at the same observed false-alarm burden.
3. Walk-forward replay may use only information available at each historical
   cutoff.
4. Missing or sparse evidence produces `NOT_ESTIMABLE`, not interpolation by
   optimism.
5. A null result retires the claim it tested; it does not become a more
   elaborate universal theory.

## Legacy note

This repository began as a 2025 concept demo called Emergence Guard. Its random
κ/ε monitor and private-kernel language were never empirical evidence and are
no longer the active project. The remaining legacy entry points are explicit
archive stubs retained so old links fail honestly.

## License

MIT © Terrynce White. See [LICENSE](LICENSE).
