# TERRYNCE-PERCOLATION-001 — frozen protocol

## Question
Does the frozen Terrynce transition construction recover known percolation critical boundaries, and does it add information beyond standard percolation observables rather than merely renaming them?

## Boundary
This is a calibration/falsification experiment, not evidence that the Terrynce Curve is a universal law. Percolation is a known phase-transition substrate with known critical points; it is useful precisely because the answer is known before the test.

## Families and ground truth
The implementation supports three preregistered 2-D families:

- square-lattice bond percolation, `p_c = 0.5`;
- square-lattice site percolation, `p_c ≈ 0.59274605079210`;
- triangular-lattice site percolation, `p_c = 0.5`.

The critical values are used only after simulation to score estimation error. They never enter the Terrynce score or its boundary estimator.

## Frozen Terrynce construction
For each family, lattice size and control value `p`, aggregate independent replicas and compute:

1. `L`: realized load — occupied-site fraction for site models, or `p` for bond models.
2. `E = 1 - component_fraction`: relief exhaustion — the fraction of local fragmentation capacity already consumed by cluster merger.
3. `A = 1 - |L - E|`: load–relief agreement, clipped by construction to `[0,1]`.
4. `S = L × E × A`.
5. The estimated transition is the `p` maximizing the central finite-difference gradient `dS/dp`.

No known `p_c`, giant-component value, susceptibility, spanning statistic, or fitted threshold may enter `S`.

## Standard comparators
On the identical simulation rows estimate `p_c` using:

- maximum gradient of giant-component fraction;
- peak finite-cluster susceptibility;
- spanning probability nearest `0.5`.

## Primary falsifier
The Terrynce construction earns no additive credit if either condition holds across the preregistered families/sizes:

- its mean absolute `p_c` error fails to beat the best standard comparator available in each case; or
- its score is effectively a re-expression of giant-component growth, operationalized here as absolute Pearson correlation `>= 0.98` over the complete sweep.

A result of `REDUCES_TO_STANDARD_OBSERVABLE` or `NO_ADDITIVE_VALUE` is a successful falsification run, not an experiment failure.

## Candidate-positive result
`ADDITIVE_SIGNAL_CANDIDATE` requires both lower mean absolute critical-point error than the best standard comparator per case and correlation below the equivalence ceiling. This remains only a candidate: it must then survive a new, separately frozen topology/constraint transfer experiment.

## Reproducibility
Default seed: `20260831`. Default lattice sizes: `16,24,32,48`. Default `p` sweep: `0.35..0.75` in increments of `0.01`. Default replicas: `32` per `(family, size, p)` cell. The runner writes raw rows, summary, protocol hash and content hashes.
