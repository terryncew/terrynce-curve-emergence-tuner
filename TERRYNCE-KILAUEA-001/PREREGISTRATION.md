# TERRYNCE-KILAUEA-001 — frozen protocol

## Claim under test
A low-dimensional, causal joint load–relief signal extracted from deformation channels can add held-out forecasting value during the repeating 2018 Kīlauea summit-collapse sequence.

This is deliberately narrow. A success is evidence for a recurring transition signal at one volcano under one unusually well-observed sequence. It is **not** evidence for a universal equation, glacier prediction, or general earthquake prediction.

## Frozen split
Use the 39 collapse cycles beginning 11 June 2018. Cycles 1–29 are calibration/training only. Cycles 30–39 are the untouched chronological holdout. No random resplitting. No threshold, sign, scale, sensor choice, hyperparameter, or data-cleaning rule may be changed after any holdout score is observed.

## Causal replay
At decision time `t`, only samples timestamped at or before `t` may enter a feature or prediction. Decision times begin at 4.8 h into a cycle, advance every 15 min, and stop 1 h before the known collapse for *evaluation only*. The collapse time can define the evaluation grid but cannot enter model features.

All scales, direction signs, regressions, thresholds, and sensor selection are fit on cycles 1–29 only.

## Terrynce joint load–relief signal
For each deformation channel `j` and decision time `t`:

1. **Load progress** `P_j(t)`: signed displacement from the cycle start, divided by a robust scale learned on training cycles only. Channel direction is learned once from the median signed end-of-training-cycle change. The scale is the training-only 90th percentile of absolute displacement at the last causally usable training sample.
2. **Relief exhaustion** `E_j(t)`: `1 - |recent causal slope| / |early-cycle reference slope|`, clipped to a fixed bounded range. Recent slope uses only the trailing 60 min. The early reference is learned from the 4.8–9.6 h portion of training cycles.
3. **Agreement** `A(t)`: cross-channel directional agreement, penalizing a joint score that is being driven by one dissenting/noisy channel.
4. Aggregate `L(t)=median_j P_j(t)` and `E(t)=median_j E_j(t)`, then freeze `S(t)=L(t) * E(t) * A(t)`.

A four-term linear ridge calibration `[1, elapsed, S, elapsed×S] → cycle duration` turns the scalar signal into a timing forecast. Ridge strength is fixed in the protocol, not tuned on holdout.

The best-single-sensor baseline uses the identical machinery on one channel at a time; the winning channel is selected using cycles 1–29 only. Therefore the joint signal loses if one sensor alone matches or beats it.

## Baselines
1. **Previous-cycle timing**: predict the next cycle duration from the immediately preceding observed duration. During chronological holdout replay, a completed holdout cycle becomes legitimate history for the next cycle.
2. **Best single sensor**: same causal load–relief recipe, one channel only, sensor selected on training data only.
3. **Published GNN**: reproduce or ingest predictions from McBrearty & Segall's released code, preserving the authors' first-29 / last-10 split.
4. **Terrynce joint load–relief**: frozen recipe above.

## Scores
Primary point-forecast checks are at 12 h (0.5 day) and 24 h (1.0 day), matching the published study's headline comparisons where a cycle is long enough to support the checkpoint.

Rolling warning evaluation asks a fixed operational question: "Will failure occur within 6 h?" Each model's training-only score threshold is chosen under the same ≤5% false-positive-rate cap, with two consecutive decision steps required to fire. Holdout metrics are timing MAE/RMSE, false-positive rate, detection rate, first valid warning lead time, and cycle-level abstention/miss rate.

## Falsifiers
The joint hypothesis loses if any of these occur:

- the held-out advantage disappears when all preprocessing is train-only and causal;
- tilt or another single sensor matches or beats the joint signal;
- the published GNN matches or beats the joint signal under the same holdout and warning constraint;
- useful performance requires normalizing by a future endpoint, full-cycle statistic, holdout statistic, or any value unavailable at forecast time;
- result depends on changing this protocol after seeing cycles 30–39.
