# Experiment progression

| Experiment | Question | Status | Design | Evidence |
|---|---|---|---|---|
| 0001 | Can local color-transition traces or ripple dynamics retrieve associations? | Implemented and measured; negative registered result | [Frozen design](../EXPERIMENT_0001.md) | [Results and failures](EXPERIMENT_0001_RESULTS.md) |
| 0002 T/R | Can configuration-dependent intrinsic oscillations transmit signals and show controlled spectral selectivity? | Implemented and measured: T negative at four hops; R indeterminate | [Frozen registration](../EXPERIMENT_0002.md) | [Results, controls and figures](EXPERIMENT_0002_RESULTS.md) |
| 0002 P | Can resonance condition persistent reconfiguration? | Deferred; not authorized for this delivery | Requires separate registration | No results |
| 0003 | How do volumetric topology and configuration affect dynamics, and can a viewer reproduce measured state? | Implemented and measured: 111 cases × two identical runs; native iGPU viewer verified | [Frozen registration](../EXPERIMENT_0003.md) | [Results and instrument checks](EXPERIMENT_0003_RESULTS.md) |
| 0004 | Do extended dual-source fields obey signed superposition in a frozen medium? | Measured: superposition within roundoff; 0/8 long-window timestep screens pass | [Frozen registration](../EXPERIMENT_0004.md) | [Results and signed fields](EXPERIMENT_0004_RESULTS.md) |
| 0004 extension | Does the current frozen AB+ signal decay over 3,072 ticks, observed every tick? | Measured: 3,073 frames; 494-tick final quiet tail, nonzero signal; prior accuracy limitation retained | [Extension registration](../EXPERIMENT_0004_EXTENSION.md) | [Results and portable report](EXPERIMENT_0004_EXTENSION_RESULTS.md) |
| 0005 | Can spatial morphology and a bounded local rule change excitation and subsequent response? | Short energy/linearity/persistent response checks pass; long numerical gate fails; M5-B gated | [Frozen registration](../EXPERIMENT_0005.md) | [Results and limits](EXPERIMENT_0005_RESULTS.md) |
| 0006 | Can multi-module morphology affect post-reset response beyond a source edit, on refined grids? | Measured: numerical screen passes; 4/4 selected structural and 8/8 selected causal gates pass | [Frozen registration](../EXPERIMENT_0006.md) | [Results and scope](EXPERIMENT_0006_RESULTS.md) |
| 0007 | Can fixed reads distinguish two retained write experiences across held-out bodies? | R2 calibrated REMOTE passes7/8 on both grids; raw R2 fails4/8; R3 operationally indeterminate after full-field refinement failure | [Frozen registration](../EXPERIMENT_0007.md) | [Results and failures](EXPERIMENT_0007_RESULTS.md), [Operation manual](OPERATIONAL_LATTICE_MANUAL.md) |
| 0008 | Which equal-energy excitation distinctions propagate through frozen morphology? | P1/P4/P6 pass; P2 fails; spatial energy distinguishes module9/27 at4 hops (8/8), fails6; dual-energy discrimination fails | [Frozen registration](../EXPERIMENT_0008.md) | [Energy, signed fields and failures](EXPERIMENT_0008_RESULTS.md) |
| 0009 | Can a saline acoustic container support validated immersed-neuron communication? | Standalone17 runs; S1/S8 FAIL from energy-report reconstruction and LOW convergence ratio; S2–S7 INDETERMINATE, conditional neural study NOT RUN | [Frozen registration](../EXPERIMENT_0009.md) | [Acoustic fields, numerical failures and diagnosis](EXPERIMENT_0009_RESULTS.md) |
| R1 | Does a working distributed association survive partial loss? | Proposed; intact retrieval prerequisite unmet | [Proposed protocol](../EXPERIMENT_R1.md) | No resilience measurements |

Experiments 0001/0002's sources, parameters, results, and raw evidence remain
unchanged. New experiments have separate runners and output folders. A software
test pass is distinct from a scientific result; an executed negative experiment
is a completed research deliverable.

## Dated record

- 2026-11-12: Experiment 0001 implemented, measured, independently verified and
  replayed. No successful association retrieval or resilience demonstrated.
- 2026-11-12 16:32:35 UTC: Experiment 0002 registration draft started; Stage P deferred.
- 2026-11-12 16:38:24 UTC: T/R registration frozen in commit `f3167f1` before
  implementation or data collection.
- 2026-11-12: T/R executed twice: 73 transport and 1,028 spectral/control cases
  per run, byte-identical evidence independently checked in Python. T fails the
  four-hop normalized-transfer criterion; R remains numerically indeterminate.
  Neither failed criteria nor thresholds were revised after inspection.
- 2026-11-13 03:34:26 UTC (Nov 12 local): Experiment 0003 registration frozen
  in `5a112c1`, before measurements; implementation checkpoint `e9d9dca`.
- 2026-11-13 UTC: 111 volumetric/legacy/control cases executed twice with
  identical evidence. Native Bevy live/replay checks matched headless data on
  Raphael iGPU. No plasticity, resonance success, memory or resilience claimed.
- 2026-11-13: Experiment 0004 frozen in `4a2283a` before measurements; two
  identical 35-execution suites, 408 full signed frames per suite. Superposition
  passes the registered tolerance; all eight long-window timestep screens fail.
  Palettes unchanged; persistent interaction traces remain deferred.
- 2026-11-13: User requested triple horizon and every tick. Extension frozen
  in `2c39004`; two byte-identical3,073-frame runs,12original-prefix comparisons,
  independently verified native every-tick replay. Quiet tail begins2579;
  no exact zero or converged-physical-model claim. Portable agent report added.

- 2026-11-13: 0005 registered in `5b97a75`, before data. 12 numerical, 25 frozen, 14 short adaptive/control cases; one identical frozen repeat. Long-window gate fails, so additional M5-B/boundary cases remain unexecuted. Both short adaptive grids produce the same 63 edits and persistent causal response after transient reset; no associative memory result. Viewer display spacing 1.8 verified natively with unchanged observation audits.

- 2026-11-13: 0006 frozen in `578870c`; 190 logical conditions =168 primary executions +22 reuses, plus one byte-identical repeat. Refined .05/.025/.0125 numerical screen passes through307.2; M5 failure unchanged. Multi-position recoloring and histogram-preserving swaps pass selected fine checks; off-source retained changes affect re-exposure under both displacement/energy conventions. No associative memory result.

- 2026-11-15: 0007 registered2cc0e00 before data, interface/decoderd7f97f0 before execution. 688 logical trajectories =496 primary+192 explicit calibration reuses;3 separate repeats. R2 calibrated REMOTE7/8 on both grids, raw4/8. Structural encoding24/24 and exact selected repeat pass. R3 reduced features are stable but seed71/W0 full-field refinement3.799% exceeds1.5%; numerical indeterminacy retained. Calibration/templates remain external; no associative recall, capacity or resilience result.

- 2026-11-15: 0008 frozen8e74e54, method325fe77 before data.97 actual cases (64primary+32fine+1repeat),582 full signed/energy checkpoints. Spatial-energy module-location readout8/8 at2/4 hops on both grids, cross-module A4 also8/8; global energy6/8, A6 fails detectability/accuracy. Energy loses inversion sign; signed UV resolves it at2/4. Effective participation never reaches registered8 at held-out checkpoints (max6.875909); dual-energy classification fails. All physical numerical gates pass; no learning/recall or nonlinear emergence claim.

- 2026-11-15: 0009 registration17ee680, standalone/methodc07dac9 before data.17 actual fluid-only executions,68 full fields,580 independent gates. S1/S8 fail:30 energy-report discrepancies>1e-12 and LOW continuum-error reduction0.869709>0.35. Summation roundoff and spatial/temporal dispersion cancellation diagnosed without changing verdicts. All445 conditional neural/calibration cases explicitly NOT_RUN; S2–S7 indeterminate. No immersed-neuron communication result.

## Experiment 0010 — numerical rehabilitation and controlled neural-fluid coupling

Independent [registration](../EXPERIMENT_0010.md), [schema](EXPERIMENT_0010_SCHEMA.md)
and [measured report](EXPERIMENT_0010_RESULTS.md). QR9 stays a historical FAIL.
QR10 separates physical accuracy, fixed-space temporal order, fixed-time spatial
order, conservation/accounting and reliability; Level A gates a stationary actual
QR-neuron pilot, while Level B gates stronger quantitative claims. Consult the
report and execution ledgers for actual PASS/FAIL/INDETERMINATE and NOT RUN states.
No overall score, plasticity, learning, memory or mobile geometry claim.

Measured:159 actual simulations,2 calibration reuses. Numerical A..E and Levels
A/B pass for registered fixtures. Emission/reception, reciprocal accounting,
controls and signed interference pass; **all9 held-out S9/S27 decoders FAIL**.
C5 retains22 resolved band comparisons and14 INDETERMINATE. Full failures,
work/uncertainty budgets and original QR9 FAIL remain inspectable in the report.

## Experiment 0011 — local temporal signatures and gated morphology

Independent [registration](../EXPERIMENT_0011.md), [schema](EXPERIMENT_0011_SCHEMA.md)
and [measured report](EXPERIMENT_0011_RESULTS.md). Identical local sensors and bounded
405-component traces in every instantiated neuron precede a registered local
morphology rule. Separate equal-source-work calibration, polarity/reordering,
quiet/disconnection/trace-off/scrambled/frozen controls, complete reset and
adapted-versus-virgin probes distinguish temporary signatures, persistent change,
causal response and held-out usefulness. Source labels/means remain apparatus.
All prior failures remain; no overall score or distributed-association claim.

Measured: all298 trajectories and73 distinct commitments executed.877 full fluid
and877 owned-neuron checkpoints, every actual tick retained. Local sensing,
causal trace reconstruction, equal-work temporal structure, legal morphology and
complete-reset causal pilot pass. Primary signed-trace source classifiers FAIL
(4/8 at4m,2/8 at6m, both grids); instantaneous-state comparisons PASS7/8 and8/8.
The retained held-out discrimination result remains a separate report verdict.
Retained held-out usefulness **FAILS** at both distances: adapted4m all ties,
adapted6m4/8 each grid; at least one paired history has zero feature separation.
Persistent causal response modification is supported; useful memory is not.

## Experiment 0012 — four-neuron shared-fluid morphodynamics

[Registration](../EXPERIMENT_0012.md), [schema](EXPERIMENT_0012_SCHEMA.md),
[results](EXPERIMENT_0012_RESULTS.md), [composition](EXPERIMENT_0012_COMPOSITION.md)
and [exploitation](EXPERIMENT_0012_EXPLOITATION.md). Original80 trajectories executed,
including2protocol-invalid conditions described below.
Three legal in-run events per node in the pilot agree across P/T/F, with full
energy/work and exact-fork evidence. M2 remote threshold FAILS: numerically resolved
remote differences are below0.1% of baseline. Independent open-operator prediction
passes agreement; categorical engineering advantage FAILS. Collective verdicts
remain separate. Initial verifier defects and original receipts are preserved in
[execution clarifications](EXPERIMENT_0012_EXECUTION_CLARIFICATIONS.md). Historical
memory failures remain unchanged; memory/learning are not0012 success criteria.
M3 fixed reciprocal interaction PASS; adaptive modulation/diversity INDETERMINATE
(seed409 refinement/event failure, seed419 valid negative). Original80 includes
2protocol-invalid adaptive duplicates mislabeled nonadaptive;78intended conditions
validly executed. A separately preregistered2-run diagnostic completes the missing
control without replacing originals or revising gates. Total82actual trajectories;
all defects, diagnostics, numerical failures and exact negative thresholds retained.
