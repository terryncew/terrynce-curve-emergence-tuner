# TERRYNCE-PERCOLATION-001 — status

Status: `FROZEN_COMPLETE / NO_ADDITIVE_VALUE`

The final preregistered construction was frozen before the default confirmatory run. An earlier smoke run was used only to exercise the harness and does not count toward the claim.

Confirmatory configuration:

- families: square bond, square site, triangular site;
- lattice sizes: 16, 24, 32, 48;
- p-grid: 0.35 through 0.75 in 0.01 steps;
- replicas: 32 per cell;
- seed: 20260831.

Result:

- Terrynce mean absolute critical-point error: `0.1849179830693`;
- best standard comparator mean absolute error per case: `0.006208991534650006`;
- Terrynce-score vs giant-component Pearson correlation: `0.9021312768623939`;
- disposition: `NO_ADDITIVE_VALUE`.

The equivalence ceiling did not fire: the score was not merely correlated at >=0.98 with giant-component growth. It still lost decisively because its transition gradient landed far from the known critical boundaries. In square-bond percolation, for example, the frozen estimator selected p=0.74 at all four preregistered sizes while the known critical value is p=0.5.

This falsifies this specific load–relief–agreement mapping as a useful percolation critical-boundary estimator. It does not falsify every possible Terrynce Curve formulation. Any revised mapping, finite-size scaling rule, or constrained-percolation extension must receive a new experiment ID; 001 is closed and must not be repaired post hoc.

Receipts:

- protocol SHA-256: `50d2062d3c6a63aef4f631bee91b70a962a6b52a7d86b3b07e9ce19d7cceaf2a`
- raw CSV SHA-256: `3354c668e9fa61a02605f9f71bf45116912b1b73d630529a55d2847a359e61d1`
- summary SHA-256: `7fbf1575117066b14236de61aea80b03e760f1d145e45e9c9a2f9ef73726f3e7`

Local validation before handoff: `6/6` tests green on Python 3.13. The confirmatory run completed in about 15 seconds in the build environment.
