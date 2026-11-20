# Experiment 0013: the external learner

Preregistered 2026-11-19 against main f23a3909294b98732cef6a55714d8c5a9121bc99,
Cognis 11 Inc., QR Morphodynamic Network. This commit precedes new extraction,
model fitting and confirmatory Rust outcomes. Existing QR12 outcomes are known;
all analyses of those data are RETROSPECTIVE. Principle002 remains proposed.
No memory/intelligence/emergence criterion. No overall success score.

## Authority, questions and protected evidence

Rust QR12 is authoritative. PyTorch is an explicitly authorized EXTERNAL scientific
instrument. It receives observations, never writes simulator state, forces,
coefficients, palettes, thresholds or event decisions. New Rust executions call
the unchanged QR12 engine/CLI with registered input matrices. No historical physics,
registration, results, archive, failure receipt or threshold is amended.

Questions: E1 forecast utility beyond matched ordinary reductions; E2 incremental
morphology information beyond current/history mechanical and sensory state; E3
latent predictive/reconstruction structure beyond PCA; E4 qualified falsifiable
hypotheses followed by separately frozen prospective physical tests. The independent
Codex proposal is a separate source-grounded document, not an automatic discovery.

QR12:80 original runs (78 intended valid conditions,2 protocol-invalid selectors)
plus2 corrective post-outcome diagnostics;615 checkpoints,82 every-tick streams.
These are NOT82 independent samples. Original remote size FAIL and adaptive seed409
numerical/event failure remain. Original M4 physical agreement PASS and engineering
advantage FAIL remain. Prior QR11 retained discrimination FAIL remains.

## Phase A: provenance, validity and partitions

Read original Quick Review and Full Evidence archives without mutation. Verify
archive SHA against QR12 delivery receipts and member/raw manifests. Extract via
existing QR12 memory-mapped readers from actual raw recordings, with checksums,
exact tick ordering, finite values, age, palette legality, event counts, metric
alignment and metadata. Bind each execution to archive SHA, raw input SHA, prior
audit receipt, seed/grid/dt/geometry, condition/policy/forcing, ancestry, node,
physical time and exact event/control state. Record checkpoint field availability;
full fields are sparse and must NEVER be interpolated into every-tick truth.

Complete inventory retains ALL82, including oracle/scalar/private/control cases.
Use actual metadata, not intended filenames. Protocol-invalid NONADAPTIVE duplicates
are excluded from modeling. Numerically invalid refined pairs are descriptive only,
not physical confirmations. Corrective diagnostics are labelled separately. No
invalid run is relabelled or used to claim superiority. Modeling uses genuine
four-body shared cases only, deduplicates exact owned-state stream hashes per seed,
and uses P data for development; F/T are paired numerical sensitivity, never extra
training/independent samples. Quiet/OFF/trace-off controls remain explicit strata.

All seed401 trajectories and causal descendants belong to TRAIN. Seed409 belongs
to VALIDATION, including its invalid exclusions. Seeds419 and427 are a separate
RETROSPECTIVE TEST; no model/normalizer/PCA selection uses them. No random temporal
split. Training observations may overlap in time; uncertainty units remain seeds,
not timestamps/windows/nodes/refinements/repeats. No optimizer may read final tests.

Prospective final seeds, reserved NOW:431,433,439,443,449,457,461,463. Each runs
FIXED and ADAPTIVE, SQ, original pulse, horizon24, both P=(48,.05),F=(96,.025):
32 new serial CPU trajectories. Same palette IDs, ports, equations, event times16,
24 and full-state output as QR12. No new law. Both policies of a seed form ONE
family. Run only AFTER freezing all selected baselines/models, preprocessing,
checkpoints and hypothesis registry hashes. No reseeding/replacement after results.
At horizon24 includes the first two registered opportunities without extending
QR12's failed40-unit adaptive regimes. Report any new event/refinement failures.

Before confirmatory interpretation independently audit every new case using QR12
mechanical/trace/work/field checks, then whole-history u/v/packet/z<=10%, full
fluid<=10%, exact palette and accepted-event agreement on P/F. P/F disagreement
makes that condition INDETERMINATE, never a negative or positive physical finding.
G2/G3/G4 require at least6 independent seeds valid for BOTH policies; otherwise
INDETERMINATE. Invalid predictions remain in ledgers, not silently dropped.

## Observations and forecast alignment

Retain full original64 u,64 v,7 packet,405 traces,64 palette and local controller
arrays via mapped raw streams; compact derived files at common physical cadence.2.
No stored PASS label is itself validation. Target at t+h uses ONLY predictors at
or before t; history t-.4,t-.2,t. Direct horizons h=.2,1,2 (physical units).
Eligible origins .4 through end-2. Windows crossing16/24/32 are flagged using
future labels ONLY for evaluation strata, not supplied as observed events.

Local observer: own u/v,packet,own energy,18 registered signed traces (QR11 first6
of each135-wide bank), latch/events/attempts/time-since-own-event, own clock.
Global observer: concatenated four-node local states plus actual global
fluid/neural/loss/work totals at current/past observations and apparatus forcing
kind. Local has no other node, global metric, seed, condition ID or target API.
Models never receive future work, future traces/palette, accepted event or scores.
Morphology variant additionally receives current own palette one-hot(64x5);
global uses all four. State-only variant with identical remaining features omits
palette. Different input parameter counts/costs are reported, not assumed matched.

Primary targets: signed full u/v, local pressure and per-node physical energy.
Global predicts all4 nodes; local is pooled/shared per-node predictor. Record
per-target/horizon/node/seed errors, especially unforced nodes and event crossings.
Macro losses use development-only target RMS scales (floor1e-8); no test fit.
Report raw RMSE and relative whole-history L2 separately to avoid source dominance.
Only u/v block decides primary G2/G3; energy/pressure secondary, not gate substitutes.
Multi-step accumulation: recursive .2 model for10steps, holding current morphology
and unpredicted sensory/controller quantities fixed, flag crossings; this is an
explicit reduced closure assumption, not authoritative physical evolution.

## Phase B: ordinary baselines BEFORE PyTorch fitting

Persistence; three-lag ridge AR; PCA (ranks4,8,16,32); PCA+ridge linear dynamics;
truncated DMD (rank8/16/32) with affine term/three-lag delay embedding as needed.
Equivalent PCA+linear delay dynamics is acceptable when mathematically identical;
name that equivalence, do not count it as independent evidence. Ridge penalties
1e-6,1e-3,1,100, chosen solely on409 validation u/v loss. Train normalizers/PCA only
on401. Fit direct horizon models with exactly matched history/palette interfaces.
Also compute spectral modes/cross-correlations/Hilbert phase with stated zero
amplitude rules, and a known-equation second-order frozen-pressure oscillator
Taylor reduction using current palette, intrinsic stiffness/damping and reciprocal
port acceleration; report omission of evolving fluid and future morphology.
Baseline selection record freezes best validation predictor BEFORE final test.
Known exact full-fluid QR12 composition remains an accurate but unreduced solver
reference; no neural superiority over it is inferred.

## Phase C: bounded external models and latent analysis

CPU f32 training, f64 physical analysis; torch manual seeds17,23,29, deterministic
algorithms enabled, one intra/inter-op thread. RTX hardware is inspected but GPU
execution not needed; CPU capable mandatory CI smoke. Pin actual installed CPU
wheel and record interpreter/dependency/configuration/environment versions.
No cross-version/platform bitwise guarantee. Repeat selected training seed17 once
to measure actual checkpoint/prediction reproducibility. Preserve failed attempts.

Forecast candidates: MLP hidden32,tanh; GRU hidden32 with3 historical samples.
Both predict persistence residuals at all3 horizons jointly, linear output.
Separate local/global and state-only/palette variants. Adam lr.001, minibatch256,
max120 epochs, best validation epoch, evaluation every5 epochs plus final; no
additional architecture/learning-rate search. Max24 forecast fits (2architectures
x2observers x2morphology x3seeds), plus one reproducibility repeat. <=300000 trainable
parameters/model; if dimensions exceed cap, stop that candidate, do not retune.
No training on final reserved seeds or retrospect test419/427.

E3: physical u/v only, compare rank8 PCA with autoencoder512->32->8->32->512
(tanh hidden/latent, linear output), max120epochs, seeds17/23/29, Adam.001. Train
only401 and select on409 reconstruction. Fit ridge evolution in each learned/PCA
latent using the same three horizons; assess reconstruction, physical-observable
energy preservation, forecasting and subspace/linear-Procrustes reproducibility.
Coordinates/clusters are not automatically modes or regimes. Optional approximate
composition: compare E(x_t+.4) against2 latent .2 maps, normalized error alongside
PCA; no functor/engineering advantage claim. Omit only if budget threatens core.

## Metrics, uncertainty and separate gates

Per-seed primary loss averages normalized u/v MSE equally over policies, nodes and
horizons. Keep local/global, fixed/event crossing and raw per-node diagnostics.
The primary chosen instrument is lowest validation-loss global architecture with
palette, fixed before testing; model seed17 primary,23/29 replication. Strongest
matched ordinary baseline chosen by validation, not a deliberately weak comparator.
A simple model may win. Retrospective test cannot alter final choices.

G1 PASS: all inventory origins/hash/alignment/units/ancestry/validity/splits and
independent extraction checks pass; FAIL on verified corruption/leakage; missing
necessary evidence INDETERMINATE and dependent work NOT RUN.
G2 PASS: primary learner improves mean paired seed loss>=10%, exact one-sided
paired sign-flip test p<=.05, >=6 valid families, and same positive direction
on F and both replication seeds. Compare SAME eligible samples. Bootstrap10000
seed-family resamples seed1300,95% interval reported; lower bound must exceed0.
Valid result missing a required criterion FAIL; unresolved numerical evidence
INDETERMINATE. Report grids and all baselines, no best-test model substitution.
G3 same threshold/test/replication requirements comparing selected palette vs
its matching state-only architecture on event-crossing u/v windows; neither
future event occurrence nor schedule prediction counts as a causal mechanism.
G4 PASS only if rank8 autoencoder beats PCA by>=10% in BOTH held reconstruction
and latent forecast losses with same seed-level p/CI requirements, both grids,
and replicates; otherwise FAIL if valid, INDETERMINATE if invalid/insufficient.
G5 requires a qualified learner-generated hypothesis and independent protocol
below. No qualified candidate =>NOT RUN, not discovery FAIL or invented success.
G6 compares counted prospective validation yield and end-to-end training/analysis
cost with baseline ranking on SAME bounded candidate set. PASS requires>=20%
more valid predictions per compute-second with exact paired p<=.05 and at least
8 independent decisions; if no independent decision experiment, NOT RUN. Forecast
inference speed alone is not efficient hypothesis selection.

## E4 candidate procedure and independent tests

After historical development ONLY, enumerate at most3 explicit candidate physical
relationships from residuals, morphology ablations or latent analysis. Registry
includes exact source observations, known-equation alternatives, geometry/energy/
work confounders, predicted variables/direction/magnitude, selection rationale,
limitations and rejection reason. Require consistent association in TWO distinct
development seed families, >=10% validation improvement beyond strongest baseline,
and a measurable candidate quantity >=5x paired numerical uncertainty. Predicting
known deterministic clock/eligibility alone cannot qualify. No independence claim
from repeated timestamps. Preserve all rejected candidates.

A qualified candidate gets a SEPARATE committed prospective registration before
new confirmation outcomes: at most32 additional serial Rust continuations total,
using unchanged QR12 complete-state permit/veto/energy-sham/isolated interfaces,
from reserved seed checkpoints with explicit controls and no reset. Freeze
quantitative predictions before branch outcomes. Keep final forecast evaluation
and candidate confirmation roles/ancestry explicit; no hypothesis selection from
final forecast outcomes. Candidate needs its frozen thresholds and >=6 valid
independent seed pairs, direction/effect >=5x numerical uncertainty and declared
energy/geometry controls. No candidate qualifies => do not manufacture interventions.
Independent proposal may challenge plan and recommend0014, but cannot alter0013 gates.

## Ceilings, stopping, audit and delivery

New physics<=64 actual trajectories,<=1800 case seconds,<=10GB raw,<=300s/case;
CPU serial; no optimizer controls physics. Model training<=1800s total, bounded
fits above; analysis/replay<=3600s; RAM<=6GB per process (source field mapping
sparse); new artifacts<=12GB excluding unchanged historical ancestry archives.
Before expansion forecast costs from QR12 empirical rates (P24~1.5s,F24~21s;
32 forecast cases~360s, fields/streams conservatively<4GB). Record actual wall,
RSS and bytes; stop expansion at ceiling with honest NOT RUN, no seed replacement.
No prerequisite failure blocks independent documentation/proposal/exploitation.

Versioned extraction/validation, schema, source/split manifests, baselines, models,
selection/checkpoint/dataset hashes, full predictions/metrics/failed fits, latent
and candidate ledgers, actual-data figures, separate G1..G6 results, exploitation
and independent proposal. Full portable evidence includes source + required
historical ancestors + every actual new raw case/model and pinned dependencies;
Quick Review includes compact observations/metrics/source and audit instructions.
Never rewrite prior archives. Fresh extraction verifies member/raw/source hashes,
rebuilds Rust and runs CPU tests plus independent reconstruction/evaluation without
refitting on tests. Local checks, archive verification, remote SHA and hosted CI
are separate receipts. Inspect diff/staged whitespace/summary, update current docs,
commit/push verified renamed remote and check exact hosted CI. No global score.
