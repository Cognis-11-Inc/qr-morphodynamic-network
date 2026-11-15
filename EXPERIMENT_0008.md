# Experiment 0008: energy distribution and lattice communication

Registered 2026-11-15 before implementation and any new-seed simulation or
classification. Baseline clean main bf92f24. The registration commit, this file
and docs/EXPERIMENT_0008_REGIONS.json identify the freeze. No pilot outcomes or
held-out data inspected; no amendments. Protected baseline hashes are in
 docs/EXPERIMENT_0008_PROTECTED_SHA256.txt. Preserve all earlier scientific files,
raw evidence and verdicts. Principle 002 is a proposed mechanism, not an
experimentally established law. This is information dynamics, not associative
memory, capacity, learning, retrieval, cognition, resilience or physical fidelity.

## Preflight and lawful reuse

Use unchanged QR6 Medium::new/advance/match_energy/energy. The constructor already
supports A, B, AB+ and AB-; reset_impulse and QR7's operator have narrower port
semantics. QR8 therefore has a new frozen-stimulus adapter and versioned records.
Negative singles invert the initialized A displacement before match_energy(1),
which refreshes the force cache. Always advance(forcing=0,history=false); never
call adapt_rule, apply_palette or a plasticity pathway. QR7's learned palettes,
read port2183, decoder and old schemas are not repurposed.

An independently integrated B27+ is necessary for the required superposition
control: heterogeneous A/B unit-impulse energies need not be equal. Add that
condition to every seed/grid. The complete matrix is64 primary +32 fine +1 repeat
=97 actual executions; zero reuses and no missing declared control. No negative
trajectory is synthesized instead of executed.

## Physics and initialization remain frozen

4096 independent8x8 palettes0..4; heterogeneous unchanged SplitMix64 initializer,
including its established module27 policy; open16^3 Cubic6, ID=x+16(y+16z).
Unit mass, internal cardinal8x8 neighbors, external matching-module neighbors.

    omega=.8+.08P+.04 occupied_internal+.12[P=1]
    gamma=.08+.01 empty_internal+.02[P!=1]
    g=.5 for0, 1 for1, .75 otherwise
    k_internal=.15*g_i*g_j; k_external=(.4/6)*g_i*g_j
    u'=v; v'=-omega^2*u-gamma*v+sum_j k_ij(u_j-u_i)
    E=sum_i(.5*v_i^2+.5*omega_i^2*u_i^2)
      +sum_undirected_edges .5*k_ij*(u_i-u_j)^2

Same serial CPU f64 split: exact half damping / velocity-Verlet / exact half
damping; same force/edge order; no clipping, pruning, GPU execution or parallel
state updates. Default intrinsic damping; no sponge, continuing force, work or
palette change. Capture every actual initial P and verify exact persistence.

A2182=(6,8,8), B2186=(10,8,8). Independently initialize each case with v=0 and
exactly the specified nonzero u at the registered module. For nonzero cases scale
all initial displacements by sqrt(1/E_unit), refreshing acceleration. E0=1 within
relative1e-12; publish actual amplitudes and independent energy calculation.

Signals: S9p=A/module9/+; S27p=A/module27/+; S9m=A/module9/-;
S27m=A/module27/-; ABp=A+B/module27/++; ABm=A+B/module27/+-;
ZERO=no excitation; B27p=B/module27/+ (superposition basis only).
All runs keep P frozen. No field is inherited from a preceding case.

Training/reference seeds101,103,107,109. Held-out127,131,137,139. Primary dt.025,
horizon32, all8 signals at each8 seeds (64 runs). Repeat all8 held-out signals at
.0125 through32 (32). Preselected exact raw repeat: seed107, ABm, dt.025, time32
in fresh repeat directory with the same physical condition ID (1). Total97.
Training32 runs finish before reference means are fitted/frozen. Preserve source,
binary and template SHA receipts before any held-out execution. Fine predictions
use those same primary-grid reference means; no fine refit or seed substitution.
Estimated serial physics time20–35 minutes, roughly5GB full fields/partitions plus
streamed diagnostics and source/analysis archives. Measurements may be negative.

## Actual module energy, motion and regions

K_i=.5*v_i^2. Q_i=.5*omega_i^2*u_i^2 plus ONE HALF of each incident edge potential
(.25*k_ij*(u_i-u_j)^2). Actual local mechanical energy e_i=K_i+Q_i, nonnegative.
Summing64 modules yields neuron energy; summing all fields yields E. Preserve K,
Q, full signed u/v and P at checkpoints. Rust observation reconstruction is
passive; compare its totals/local partitions against unchanged Medium::energy.
Python independently reconstructs coefficients and half-edge partitions from P,
u,v using tensor slices, not the Rust edge list. Never substitute squared activity
or a palette proxy for mechanical energy.

Motion energy m_i=.5*v_i^2+.5*omega_i^2*u_i^2 excludes edge allocations. Half-edge
energy is present in adjacent neurons/modules at time0 even when they have zero
u/v. Record that initial allocation honestly; primary arrival uses motion energy,
so it does not mistake potential-energy bookkeeping for arrival of excitation.
No integrated edge-transfer amount is claimed from instantaneous power. Regional
energy change also includes damping and boundary-edge allocations.

For d=1,2,3,4,6: A_d = nodes exactly d Cubic6 hops from A; F_d = nodes with
min(hops(A,node),hops(B,node))=d. Decoding excludes BOTH A and B in every case.
A shells describe propagation from A; F shells measure dual-source discrimination
beyond BOTH potential sources. B's initial presence at A-distance4 is explicitly
reported in full A-shell energy, and never called transport from A.

Exact sorted receiver memberships and six decoding probes per region are frozen
in REGIONS.json. Probe selection is geometry-only farthest-point sampling:
start lowest ID, then maximize minimum Cubic6 distance to selected IDs, ties
lowest ID, until6; sort final IDs for feature order. Same6-sensor budget at every
distance and for every input/seed/grid, no selection from activity or morphology.
Full shell distributions remain available independently of the six-sensor decoder.

Every tick record: E components, exact damping loss, drift/max|u|/|v|; full-population
energy participation (sum e)^2/sum e^2, non-source motion-active neuron count,
other-than-injected-module mechanical/motion energies, and other-than9/27 energies.
For each10 region: full geometric shell mechanical energy (A includes B if d4),
receiver mechanical energy and fraction E, receiver motion energy, other-injected
and other9/27 receiver mechanical/motion energy, min/max/mean/std receiver neuron
energy. ZERO fractions/participation are0, not NaN. Units are model units.

Every tick stream the fixed union of decoding probes plus A,B,2184,0,4095:
per-neuron mechanical/motion energy and signed u/v at modules9,27,10,18. Full
checkpoints at0,.8,3.2,8,16,32, no interpolation. Nonzero observation times for
features are .8,3.2,8,16,32. Every-tick samples are measured, not an every-tick
full-field reconstruction. Earliest crossing, peak and peak time use actual ticks,
no fitted arrival or phase alignment. Physical time is tick*dt.

## External, fixed discrimination; observation budgets

Four binary comparisons, class0 then class1:
LOC=(S9p,S27p), SIGN9=(S9p,S9m), SIGN27=(S27p,S27m), DUAL=(ABp,ABm).
No ZERO/B27p training class. No virgin calibration subtraction or normalization.
No learned internal network, weights, reward, imposed palette encoding or updates.

Global G: E at5 times, dimension5, includes the sources by definition. It cannot
establish a distal result. Every A/F region has all-modules and CROSS variants;
CROSS excludes BOTH directly stimulated channels9/27, keeping62 modules. Same
mask is used for all input comparisons, even when only one module is stimulated.

For each region/mask, fixed raw features in time/probe-ID/module/component order:
T: per-module total e=K+Q, 5*6*M components (primary spatial energy).
U: signed u, same dimension and observation positions as T (matched budget).
KP: per-module(K,Q), 5*6*M*2 components, no sign information.
UV: signed(u,v), exactly the same positions and dimension as KP (primary complete
signed readout, with budget-matched KP comparison). T versus U and KP versus UV
are budget-matched; comparing T to UV alone doubles the scalar observations and
is explicitly labeled. SH: total receiver energy of selected modules over the
entire region at5 times, dimension5, budget matched to G in number of scalars;
its larger spatial coverage is explicit. All representations reported separately.
For M=64, T/U have1920, KP/UV3840 components; CROSS has1860/3720. SH always5.
No nearby/far concatenation, no cross-distance feature pooling, no whitening,
frame normalization, feature pruning, phase adjustment or outcome-dependent scale.
Diagnostic fractions of retained energy do NOT enter the classifier.

For each pair/representation/region/mask independently, mean class vectors across
training seeds in ascending order, sum then divide4. Freeze all404 two-class
reference templates (4 pairs*(1global+10regions*2masks*5representations)). Predict
nearest mean by squared Euclidean distance. If abs(d0-d1)<=1e-12*max(d0,d1,1e-30),
record AMBIGUOUS, count incorrect; no favorable forced class. Nonfinite input/model
invalid. Classifier receives numeric vectors only; seed, class, condition, P and
metadata are external indexing/audit records, never features. Expected label is
compared only after numeric prediction. These are finite deterministic cases,
not independent random trials yielding population accuracy or channel capacity.

## Preregistered detection, reliability and discrimination gates

Every nonzero case E0 matched within1e-12; every tick finite |u|,|v|<=100 and
abs(E-E0+intrinsic_loss+boundary_loss)/max(E0,1e-12)<=1%. Forcing/switch work0.
ZERO has exact zero u/v, K/Q, diagnostics and histories. P bytes never change.
Recorded module partitions must independently match (relative combined L2<=1e-12,
max absolute component error<=1e-12 E0, total absolute error<=1e-10 E0); zeros exact.

All nonzero held-out checkpoints .8..32 require unaligned combined full u/v
relative L2<=1.5% (.025/.0125, denominator fine norm floor1e-30). This inherits
QR6's registered short-window bound, not QR7's adaptive R3 exception. QR7 virgin
calibration max observed .186504% and fixed-morphology QR6 short tests motivate
retaining, not loosening,1.5%. No inference of accuracy beyond32 or physical law.
QR4/QR5 historical timestep failures and QR7 R3 failure remain unchanged.

SIGN controls: at every checkpoint, inverted u/v sums have relative L2<=1e-12
and absolute RMS<=1e-14; K/Q and every-tick global/shell energies agree to relative
L2<=1e-12 and max absolute<=1e-12 E0. At zero fields use denominator floor1e-30.
Energy is even under full inversion; signed trajectories are odd. Exact byte
identity of positive/negative energy records is reported if present, not assumed.

Superposition: compare ABp/ABm full signed fields at all checkpoints with
alpha*A27p +/- beta*B27p, where alpha=actual_AB_A_amplitude/actual_A27p_amplitude,
beta=abs(actual_AB_B_amplitude)/actual_B27p_amplitude, from their independently
executed E1 bases at the same seed/grid. Relative L2<=1e-12, absolute RMS<=1e-14.
Do not add energy trajectories: quadratic cross terms are allowed and measured.
All source amplitudes and E_unit calculations are retained; no assumed1/sqrt2.

Absolute arrival threshold=1e-8 E0 on receiver motion energy. Energy features
pair separation floor=1e-8 in Euclidean model-energy units; signed U/UV floor=1e-6
in model-field units. E0=1 throughout. These are conservative measurement
conventions, not natural constants or capacity measures: above energy matching/
reconstruction tolerances by four orders, and above the field-roundoff controls
by eight orders. A unit-displacement analytic quadratic fixture and sign controls
validate interpretation before new-seed data; no fresh-seed threshold calibration.

Per held-out seed and each decoder: fine class separation S=norm(x1f-x0f),
D=max(norm(x0c-x0f),norm(x1c-x1f)); require S>absolute floor and S>=5D.
Each label's coarse/fine feature relative disagreement<=5% (fine norm floor1e-30).
Fine uses coarse-trained means, no refit. To PASS discrimination: at least7/8
held-out correct on BOTH grids, no ties, identical predictions on all8, all
relevant physical/field/feature/margin gates. Per-decoder verdict priority:
invalid physical/full-field or >5% feature refinement => INDETERMINATE;
S<=absolute floor => FAIL detectability; resolved S but S<5D => INDETERMINATE;
otherwise failed accuracy/ties/prediction agreement => FAIL; else PASS.
Thus invariant energy under sign inversion is a measured expected FAIL of
energy discrimination, not manufactured numerical information from roundoff.

## Separate scientific verdicts

P1 propagation: for each A-only single input and held-out seed, motion arrival at
all5 A receiver shells by32, threshold1e-8; arrivals nondecreasing with distance.
Coarse/fine arrivals differ<=.1 time and peak shell motion energies<=5% relative.
Report each input/distance and failures. P1 PASS only if all registered pairs pass;
invalid full-field/energy evidence => INDETERMINATE. B/dual propagation is descriptive,
not a claim all their energy originated at A. Total-energy crossings also recorded.

P2 redistribution: for each of6 primary nonzero signals and held-out seed, at
some registered checkpoint .8..32 on BOTH grids, total-energy participation>=8,
at least8 non-source neurons with motion energy>=1e-8, and motion energy outside
the actual injected module>=1% retained E. Use the SAME checkpoint for all3
conditions within a run; it may differ between grids. This tests spreading across
neurons/modules beyond initial half-edge bookkeeping. Report initial participation
and other-module energy separately. Invalid physical/fine fields => INDETERMINATE.

P3 information preservation: LOC/T/all at A2, A4, A6 separately. Primary distal
P3 is A4; A2 is the near comparison, A6 the additional distal test. No merged score.
SH, KP, U, UV and CROSS results are independently reported secondary measurements.
P4 representation limits: primary sign resolution requires SIGN9 and SIGN27
energy-only G/T/KP/SH to fail detectability by invariant-energy controls, while
UV/all at A2 and A4 passes discrimination. Also report symmetry verification
separately and the full G versus spatial versus signed comparison table for every
pair/distance. P4 FAIL if required signed discrimination fails despite valid
physics; INDETERMINATE for relevant invalid numerics. A failed raw class-mean
readout alone is not a theorem that no decoder could distinguish that input.
P5 interaction: DUAL/T/all at F2 and F4 separately; primary distal P5 is F4,
F2 near and F6 secondary. All receivers are beyond BOTH sources at that distance.
Signed superposition must pass; any failure is a reliability failure, not emergence.
P6 numerical reliability: all matching/drift/zero/frozen/partition/symmetry/
superposition/repeat and all held-out full-field refinement gates pass. Specific
feature/margin validity remains per-readout; P6 does not override failed P3/P5.
No overall score combines P1..P6. No inference of associative recall or emergence.

## Records, tests and delivery

QR8FLD01/schema1 explicitly records signal, A/B ports, actual amplitudes and
complete condition ID, seed, dt, tick, module, P/full signed u/v plus full K/Q
module-energy fields and integrity checksums. May embed unchanged QR6 field body,
never use its source-assuming observation conversion. Full condition IDs belong
in the frame body, unlike QR7's external-only identity. Per-case parameters,
all-tick diagnostics/region/probe streams and ledger distinguish COMPLETE/FAILED/
NOT_RUN; preserve interruptions, never overwrite a case or silently reuse it.
Features contain numeric observations only; external means, labels, folds and
predictions are separate. New formats have exact lengths, finite screens and
corruption tests. Source/data SHA manifests are integrity, not authentication.

Independent Python checks all module partitions, shell membership and energies,
probe/stream checkpoint consistency, scalar diagnostics/arrival/spreading, signed
controls, all features/means/predictions and P1..P6, not checksum-only approval.
It is not a second full ODE integration. Source-bound caches also bind every input
SHA. Portable numeric review can reproduce classification without full fields;
full-field archive permits all original energy/refinement checks. Include all
compile-time root/docs Markdown and tracked test fixtures in source archives and
test a fresh extraction/build/provenance path, including a Git-free extraction.

Rust tests use unregistered synthetic/analytic fixtures for half-edge partition,
coefficient parity, signed inversion, interference energy, arbitrary B initializer,
frozen state, schema/corruption and deterministic prefix. Python tests validate
energy partitions, geometry, analytic sign limits, decoder/ties/training isolation
and rejection of missing/malformed evidence. No new-seed confirmatory runs until
registration and implementation/measurement-method source are committed.

Deliver measured report, actual spatial-energy/signed figures (fixed scales, no
per-frame normalization), complete ledger, raw observations, viewer-free packages,
full signed archive, reproduction instructions; update README/HANDOFF/index.
No new Bevy mode is necessary. Existing spacing1.8/iGPU default remain unchanged;
no native-viewer witness or FPS claim from headless checks. Local root/Python/
isolated-viewer quality gates, staged whitespace/diff/targets, preservation hashes,
commit/push/remote-SHA and exact hosted CI are separate delivery evidence.
