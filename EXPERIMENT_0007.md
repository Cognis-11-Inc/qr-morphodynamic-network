# Experiment 0007: operational encoding and standardized remote readout

Registered 2026-11-15, America/Toronto, before implementation and confirmatory
measurements. The registration commit and SHA identify the freeze. Baseline main
e3255da is clean. No calibration/pilot or held-out outcomes have been viewed.
No amendments. User directive is a proposed design; this is the actual protocol.
Preserve 0001–0006 sources, registrations, reports and raw evidence; protected
hashes are in docs/EXPERIMENT_0007_PROTECTED_SHA256.txt. Principle 002 is proposed.
No distributed association, capacity, interference, resilience or cognition claim.

## Preflight and reuse authority

QR6 Medium::new initializes the established seeded independent palettes and
cached coefficients. Medium::advance is the serial f64 split integrator;
Medium::adapt_rule calls the frozen morph_palette rules; apply_palette rebuilds
all onsite/symmetric edge coefficients and records switch work. reset_impulse
clears u/v/V/H, clock and audit accumulators retaining P. match_energy computes
actual quadratic energy and refreshes the force cache. All are reused unchanged.

QR6 reset_impulse directly supports source2182 only. A new QR7 adapter first
resets to zero, installs a unit displacement at authorized port2182 or2183, then
uses match_energy(1) to scale u and refresh cached force. No subsequent forcing.
Old QR6 metadata assumes source2182; therefore QR7 needs an explicitly versioned
port/operation recording, not a widened or misleading QR6 file. No viewer change
is needed for scientific completion. Operational controls are explicit external
interventions; adaptive writing never receives a target palette or class template.

## Physical substrate and local rules remain frozen

4096 independently owned8x8 palettes0..4, open16^3 Cubic6, ID=x+16(y+16z).
Internal cardinal8x8 graph and external matching-module links are distinct.
Active independent channel1; other three remain exactly zero. Same QR6 mass1,
omega=.8+.08P+.04occupied_internal+.12[P=1], gamma=.08+.01empty_internal+
.02[P!=1], g=.5/1/.75 for empty/matching/other color. k_internal=.15*g_i*g_j,
k_external=(.4/6)*g_i*g_j; no boundary renormalization or wrapping.
Energy=sum(.5v²+.5omega²u²)+sum_undirected .5k(u_i-u_j)².
Exact half damping / velocity-Verlet / exact half damping, same edge order.
No GPU physics, parallel updates, clipping, pruning, hidden drive or optimizer.

V=integral v², H=integral(v²+.25 mean_internal(u_m-u_q)²), trapezoidal[0,8].
S=H+.5mean_internal(H_q), own-neuron scores. R2 primary: qualify S>=1e-8 AND
S>=.05*Smax, rank score descending/module ascending, recolor up to8 by(P+1)%5.
R3 secondary: unequal-color cardinal edges, both S>=1e-8, at least one>=.05Smax;
rank sum descending/(m,n)ascending, greedily up to4 module-disjoint old-P swaps.
No minimum count. One synchronous commit at8. R3 preserves each tile histogram.
Keep every pre/post u/v fixed, record total/per-neuron switch work Epost-Epre.
The adaptive system is externally actuated, never assumed energy-neutral.

## Operational interface

CALIBRATE: virgin P only, frozen physical reads; store reference observations
externally. It is not a palette write or intrinsic calibration memory.
WRITE: from restored virgin P and exact zero transient state, source2182, W0
module9 or W1 module27, actual mechanical E0=1, v0=0. Advance through8, collect
V/H/S, commit R2 or R3 once. No further post-write dynamics are collected.
RESET: u/v/V/H and all audit accumulators/tick become exactly0, P byte-identical.
READ: after RESET, plasticity OFF. Read port2183, module9 then27 as separate
fresh-reset pulses, each actual E0=1; each runs through32. No label-dependent
pulse, port, timing, scaling policy or feature selection. P remains frozen.
RESTORE: RESET then reinstall an externally saved virgin palette. This is an
external intervention, not intrinsic erasure/forgetting. Initial P backups,
calibration and decoder templates are external apparatus, not lattice memory.
CONTROL_INSTALL: after RESET only, construct the registered subset/shuffle from
an authentic recorded WRITE outcome; no arbitrary desired-answer palette API.

Use seed-specific virgin P generated once by the unchanged initializer. Required
states/allowed transitions are checked. READ rejects an unreset WRITE state;
CALIBRATE rejects nonvirgin P. RESET has an all-element exact-zero audit, and
READ initial full fields independently verify that only its declared pulse is
present. All rule/energy/history state is reset between pulses. Read pulse
amplitude=sqrt(1/E_unit) depends on measured current stiffness, not the write
label. Publish amplitudes. This state-dependent energy controller is part of
the apparatus. No unit-displacement read arm is collected or inferred.

## Seeds, stages and immutable controls

Training:7,19,31,43. Held out:59,71,83,97. These are eight fixed configurations,
not independent random trials supporting a population accuracy estimate.
For each seed, both W0/W1 under both rules. Primary dt.025. Before any held-out
execution, finish the training stage and freeze both rules' calibrated and raw
REMOTE_ONLY templates with integrity receipts. Source/decoder code is committed
before confirmatory data. No later feature/threshold fitting or model selection.

Controls per written history:
VIRGIN: original P; ALL: full actual Pafter; WRITE_PORT_ONLY:only2182 edited;
READ_PORT_ONLY:only2183 edited; REMOTE_ONLY:restore both2182/2183 to virgin while
retaining every other actual edit; SHUFFLED: QR6 seeded SHUFFLE_POSITION of ALL,
matching changed IDs/counts and graph-distance distribution; R3 histograms exact,
R2 color-change histograms not necessarily matched, R3 control swaps may be
non-cardinal. FROZEN: complete same write exposure/histories without commit.
NO_WRITE: full8-unit zero-input exposure with rule enabled, then reset/read.
No additive percent contribution interpretation. REMOTE_ONLY is primary.

Exact matrix and execution budget:
- Coarse writes:8 seeds x2 rules x(2 active+2 frozen+1 quiet)=80 executions.
- Coarse calibration:8 seeds x2 pulses=16 executions.
- Coarse logical reads:8 seeds x2 rules x2 symbols x8 controls x2 pulses=512.
  Five nonvirgin variants require320 new reads. VIRGIN/FROZEN/NO_WRITE are192
  explicit calibration reuses, justified by identical complete read initial
  conditions, frozen rules and exact reset/unchanged-P audits. Never pretend
  reused calibration frames are newly observed or relabel their provenance.
- Fine confirmation:ALL FOUR held-out seeds, both rules, both symbols,
  dt.0125.16 active+16 frozen+8 quiet writes=40;8 calibration pulses and32
  REMOTE_ONLY read pulses=40 reads. Other controls are coarse descriptive arms,
  not silently certified by somebody else's finer run.
Total688 logical conditions:496 primary executions +192 reuses. Training stage
208 actual/304 logical, evaluation208/304, fine80/80. No condition dropped after
seeing outcomes. One preselected seed31/R2/W0 active write and its REMOTE_ONLY
module9/27 reads repeat in a fresh root:3 further executions,499 actual total.

Estimate using QR6 measured costs:~60–80 serial CPU minutes plus analysis;
~12GB full fields before compression. Every-tick global/reduced signed traces
stream to disk, not full fields each tick. No resource-unsafe parallel replicas.
If interrupted, retain exact attempted/not-run/failure ledger, never claim688
actual executions. No multiple sequential writes, capacity or damage experiment.

## Read features and frozen decoder

Output sites2184,2185,2186 (exclude write/read ports). Observe signed u AND v
at modules9 AND27, times .8,3.2,8,16,32, for BOTH standardized read pulses.
Exactly120 components in this order: read pulse[9,27], time ascending, output
site[2184,2185,2186], observation module[9,27], field[u,v]. No peaks, envelopes,
absolute-value features, outcome normalization, seed IDs, labels, condition names,
palettes or eligibility enter the classifier. Metadata is in a separate ledger.
The classifier accepts only fixed-length numeric arrays and frozen templates.

Primary preprocessing x=raw_read_feature - same-seed virgin CALIBRATE feature.
No further scaling, whitening, normalization, feature pruning or fitted weights.
For R2, form class means for W0/W1 from REMOTE_ONLY training seeds ONLY, summing
seeds7,19,31,43 in that order and dividing by4. R3 independently forms its own
secondary REMOTE_ONLY means, never substituted for R2 after results. Apply each
rule's same two templates unchanged to all its control variants. No per-variant
retraining. Raw uncalibrated means/decoding are separate secondary models.

Nearest template by squared Euclidean distance over120 signed components.
If |d0-d1|<=1e-12*max(d0,d1,1e-30), mark AMBIGUOUS, count incorrect; do not force
a favorable label. Nonfinite features fail validity. The two training classes
use supervised operator labels only to construct external means; those means
never alter P or the physical READ. Held-out labels are compared AFTER prediction.
Record all training/held-out results, distances, errors and ambiguous cases.

Primary success:REMOTE_ONLY/R2 calibrated held-out accuracy>=7/8 BOTH grids,
no ambiguous cases, identical coarse/fine predictions on all8 held-out cases,
and all numerical/structural gates below. R3 reported separately under identical
criteria. Raw classification uses its own predeclared means and same criteria.
Calibrated-only success is calibration-dependent operational discrimination,
not autonomous retrieval. A/B structural or causal success cannot replace a
failed decoder; no feature retuning on held-out observations.

## Independent numerical, structural and causal verdicts

All recorded fields finite, |u|/|v|<=100; stop/retain failure without clipping.
Energy matching relative error<=1e-12. Every-tick drift |E-E0+loss-switch_work|/
max(E0,1e-12)<=1%. Exact zero exposures remain zero and make no edits. Frozen
writes and all reads preserve P bytes. RESET retains P, zeros every transient,
history and audit value. Per-neuron energy attribution uses QR6 half-edge rule.

Fine confirmation covers every held-out REMOTE_ONLY class for both rules.
All nonzero READ checkpoints require unaligned combined u/v relativeL2<=1.5%
(.025/.0125, denominator finer norm with floor1e-30). Both writes' selected edit
positions require Jaccard>=.90 across grids (union0 gives1); publish full actual
palette equality/differences rather than only count agreement. Full signed
fields and reduced-feature validity are distinct tests.

For each held-out seed/rule and preprocessing mode, let x0f,x1f be fine read
features (calibrated if that mode is calibrated), and x0c,x1c coarse. Require
S=||x1f-x0f||>1e-10 and S>=5*D, where D=max(||x0c-x0f||,||x1c-x1f||).
Require each feature relative refinement error<=5%, denominator max(||xf||,1e-30).
This separation margin is frozen before measurements and cannot be replaced by
phase-aligned comparisons. Fine predictions use the SAME coarse-trained model,
with fine virgin calibration, no fine training or template refitting.

Structural encoding: W0/W1 Pafter differ in each seed, persist through reset;
selected held-out edit refinements pass. Repeatability: preselected raw files
byte-identical on same machine/toolchain; no cross-platform bit promise.
Remote causal effect: each held-out raw REMOTE_ONLY versus virgin feature norm
difference>=1% (denominator max(||virgin||,1e-30)), both grids, with valid energy/
field tests. This does not imply decoding. Report variants and calibration/raw
results independently. A numerical failure makes operational verdict INDETERMINATE,
not a manufactured success or a redefined threshold. Ties are failures, not hidden.

## Data, tests and delivery

Dedicated QR7FLD01/schema1 records explicit port, module, operation, rule, seed,
condition identity,dt,tick,actual P/full signed u/v and FNV integrity checksum.
QR6 sources/schema/caller semantics remain unmodified. Read checkpoints0,.8,3.2,
8,16,32; write snapshots0,8pre,8post. V/H/S and actual edits saved for all writes,
including frozen/zero controls. Global mechanical diagnostics every tick;
reduced output signed traces every tick; exact RESET/RESTORE/state-equivalence
receipts and external control provenance retained. No fabricated interpolation.
Raw features are120 f64 only; fold/label/seed metadata and predictions are separate.
Templates external, versioned/checksummed, frozen before evaluation. FNV/SHA are
integrity checks, not authentication. Portable package includes all actual
palettes/histories,features,classifications,source/rules/ledger; full fields may
ship separately. Large recordings stay ignored, source/report/figures in Git.

Rust tests use synthetic/unregistered seeds for interface transitions, exact
energy/zero/reset/restore, frozen reads, R2/R3 regression, illegal commands,
serialization/corruption and pure decoder/tie/train isolation. Independent Python
reconstructs energy, edits from histories,120features from signed checkpoints,
calibration/class means/predictions, margins and all verdicts. It independently
integrates histories at recorded probes where available; not a second whole-
network integrator. No scientific claim from compile/tests/UI alone.

Update README,progression,HANDOFF,new results/schema and measured Operational
Lattice Manual. Manual must state each operation's exact input/state/result,
energy consequences/reproducibility/limitations, and mark failed/proposed ability
as such. No viewer dependency or unsupported capability claims. Run all root/
Python/isolated viewer quality gates,check55+ historical hashes,diff/target/staged
checks,push source/results separately,verify remote SHA and exact hosted CI.
