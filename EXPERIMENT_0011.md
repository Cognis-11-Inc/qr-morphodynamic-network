# Experiment 0011: the listening QR neuron

Registered 2026-11-18, clean baseline main41c01eb. This separate commit freezes
all methods/criteria before new outcome evidence. Preserve0001-0010, especially
QR10's nine failed held-out decoders, QR7 R3 numerical failure and prior long-time
failures. Protected baseline manifest excludes only README,HANDOFF,index,lib exports.
Principle 002 is a proposed mechanism, not an experimentally established law.
No distributed association, useful memory, learning or scaling result is assumed.

User hypothesis, preserved:

> A QR neuron can locally accumulate a structured temporal signature of fluid-mediated disturbances, and repeated exposure can produce persistent, causally testable changes in its internal morphology.

## Questions, boundaries and lawful adapter

L1 sensing has separate causality, zero/disconnection, determinism, refinement
and polarity-information verdicts. L2 tests online bounded causal history and
within-seed structure, separately from between-seed variation. L3 tests equal
external work, temporal/polarity controls and fixed held-out readouts. L4 tests
legal persistent local morphology and causal ablations. L5 tests response after
complete reset, exposure specificity and held-out usefulness separately.
Every question PASS/FAIL/INDETERMINATE; dependencies NOT RUN when gated.
No overall success score. Finite deterministic seed cases are not population
accuracy estimates. External readout is an instrument, never autonomous recognition.

Use a NEW isolated-neuron module. QR6/QR7 require4096-neuron frames; their
apply_palette/reset APIs cannot be called on QR10's private isolated Neuron.
Copy QR10's intrinsic/internal-cardinal equations, edge order, half damping/
Verlet/half damping and exact reciprocal rotations; reuse unchanged acoustic0010
Fluid. No edits to prior physical modules. Initial palettes use unchanged generator
IDs2182,2186; third node2184. New adapter rebuilds coefficients at fixed u/v,
records Epost-Epre switch work, and owns explicit bounded reset state. QR6/QR7
supply constraints/work identities, not silently transplantable API compatibility.
CPU serial updates, no GPU, conventional NN, optimizer, parallel physics or clipping.

Same QR10 domain[0,24]^3, rigid walls, fourth-order staggered spatial derivative,
second-order split, normalized c=1 and engineered QR9 physical mapping. Source
(10.5,12.5,12.5), observer source+(d,0,0). beta.1 at modules9/27, normalized tensor
hat radius1.5m, exact pressure/neural-v rotations in ascending/reverse half sweeps.
No direct QR edges. All instantiated neurons have IDENTICAL sensing/tracing/
morphology code and independently owned state. Source/receiver names are external
apparatus roles only. No biological sensor material model or energetic trace
storage is asserted: these are explicit computational state variables.

## Local sensing and trace law (candidate, not a QR law)

After each COMPLETE physical step, including both external force half kicks,
sample at each node's own finite-support transducer. Weighted pressure q;
weighted cell-centred velocities (average adjacent faces, implicit wall0);
weighted fluid cell energy density with half-face kinetic sharing; current-step
net work INTO neuron/dt (negative of local fluid transfer); dq/dt from OWN prior
pressure. Packet order[q,wx,wy,wz,e,power,dqdt]. Initial packet/derivative0.
Sampler touches only nonzero local-kernel indices. Neuron.record accepts this
packet and dt, own u/v/P and own previous state: NO Fluid/global-state reference,
source IDs, seed, class, other neurons, predictions, future samples or CSV replay.
External scientific observer retains complete state for independent reconstruction.
Read-only sampling exerts no force/work and must preserve reference physics.
Source internally actuated motion can create its own module eligibility even
when fluid is disconnected; distinguish that from zero fluid sensory channels.

Three timescales tau=(.5,2,8) normalized units span carrier periods6..12, travel4/6
and inter-pulse quiet4; dt<=.05 resolves the shortest tau by>=10steps.
For EVERY component: z'=a*z+(1-a)*phi, a=exp(-dt/tau). This exact ZOH update of a
causal piecewise-constant input has |z|<=1 from initial0; no clipping is allowed.
Signed saturation B(x,s)=x/(s+abs(x)); positive B uses same formula for x>=0.
Seven sensory channels use s=(.01,.01,.01,.01,.0001,.0001,.01), fixed units
and scales informed only by prior QR10's input/receiver ranges, not new outcomes.

Each neuron also owns per-module banks at all3 taus:
H_m=v_m^2+.25*mean_internal_neighbors(u_m-u_j)^2, phiH=B(H_m,1e-8);
C_m=v_m*q_local, phiC=B(C_m,1e-6). All computed from simultaneous own fields.
Total3*(7+64+64)=405 f64 trace components per neuron (3240bytes), fixed capacity,
plus128 transient mechanical fields and7 local sensor values. No growing buffer.
Global signed channels preserve polarity; e and power are even under COMPLETE
field/force sign inversion. H and C also even. No claim energy-only channels
encode complete sign information. Every actual tick's packet,u/v,traces exported.

TRACES_OFF leaves all banks exactly0, sensing active. SENSOR_OFF leaves local
packets and banks0, physics unchanged. SCRAMBLED updates normally then cyclically
permutes each64-module H/C bank by one coordinate at each integer own local time;
this causal artificial anatomical disruption preserves each bank's instantaneous
multiset, has no future/external history and leaves global sensory banks unchanged.
It is not claimed to be a naturally occurring disturbance. QUIET no forcing;
OFF disconnects all ports but keeps the specified source force.

## Numerical budgets and mandatory prerequisites

Primary P=(N48,dt.05); temporal T=(48,.025); spatial F=(96,.025).
Full acoustic refinement uses q restriction by averaging eight fine cells;
coarse positive normal face velocity equals average of four transverse fine
faces on the same physical face (fine normal index2i+1). No phase alignment.
At registered nonzero checkpoints require restricted full fluid relativeL2<=10%,
full signed neuron u/v<=10%, local packet and trace whole-history relativeL2<=10%
(denominator finer norm floor1e-30). Report absolute RMS and per-channel errors;
relative comparisons of vanishing individual channels are descriptive, not divisions
by instantaneous zero. Actual primary/fine energy+loss-work-switch residual<=1%
max cumulative positive external work (zero denominator floor1e-30). Independent
checkpoint energy, kick work, exchange cancellation and switch work reconstruction
relative<=1e-12 of max positive supplied work, actual stored energy,1e-30.
Every physical field/packet/trace finite, |z|<=1+1e-14; rigid wall slots exact0.
Full physical-state reference agreement with QR10 <=1e-12 relative; exact bit
agreement also reported. Sensing on/off physics must agree bit-for-bit.
Online trace replay from measured packets/u/v independently within1e-12 absolute.
No numerical normalization, hidden energy correction, seed replacement or retuning.

L1 ALL five component gates required before pilot. Pilot L2 MECHANISTIC validity
requires exact causal reconstruction/bounds/reset plus <=10% refinement; L2
STRUCTURE requires polarity odd/even tests and order contrast >1e-8 in signed
trace norm and>=5x max grid disagreement. L3 equal-work calibration must pass.
These prerequisites authorize bounded morphology testing independently of the
separate held-out source-identity decoder verdict. A failed decoder is retained,
not a reason to suppress a lawful test of persistent response modification.
If mechanistic/structure prerequisites fail STOP dependent main/morphology work.

## Frozen physical inputs, calibration and phases

General exposure horizon48. MID angular frequency2pi/8. Pulses start0,16,32,
each lasts12, force=amplitude*sign*sin(omega*localtime)*sin(pi*localtime/12)^2,
midpoint sampled and applied as exact half kicks before/after free step.
S9 and S27 inject only the corresponding source module, signs[+,+,-].
ORDER injects9 signs[-,+,+], same absolute force envelope; NEG is complete
S9 inversion[-,-,+]. SINGLE injects9 only the final32..44 pulse, sign-.
SINGLE versus TRIPLE tests repetition with equal total net work; differing recent
amplitudes after calibration remain a limitation, not proof repetition is necessary.
QUIET amplitude0. No forcing after44. Only end48 morphology commitment permitted.

Each active physical case has its OWN separate unit-amplitude frozen-morphology
calibration trajectory, with sensing/traces disabled. Calibration fitter reads ONLY
actual source external net work Wunit, requires finite positive Wunit, then fixes
amplitude=sqrt(1/Wunit) before the independent measured trajectory. Target net
external work1, error<=1e-10 (thousands of f64 kicks; well below1% field budget).
Fitter receives no receiver trace, response, class result or held-out outcome.
Calibration known input module is actuator configuration, never neuron metadata.
Save force, net/positive/negative work, emission/backflow and receiver energy.
Equal external work is NOT equal emission. QUIET exempt with target0. OFF,
TRACES_OFF,SCRAMBLED reuse the physical S9 amplitude explicitly and report actual
work; OFF is not asserted equal work. No amplitude is tuned after receiver readout.

L1 reference-only seed211, LOW angular2pi/12, single pulse0..12,horizon24,
amplitude1, original QR10 two-neuron d2 arrangement.13 executions:
positive on P/T/F(3); NEG P/F(2); QUIET P/F(2); OFF P/F(2); SENSOR_OFF P(1);
positive P independent repeat(1); original three-neuron d4 IAB+ and IAB- on P(2),
third position(10.5,14.5,12.5). Compare actual QR10 stored fields/neuron states
on original conditions; retain source SHA. No new training/held seed is used.

PILOT seed301,d4: S9,S27,ORDER each P/T/F =>9 calibrations+9 measured.
NEG and SINGLE each P/F =>4 calibrations+4 measured. QUIET,OFF,TRACES_OFF,
SCRAMBLED each P/F =>8 physical controls, plus S9 P raw repeat1.
Total35 pilot physical executions. Calibrations are not decoder-training cases.

TRAIN seeds307,311,313,317; HELD331,337,347,349. Both d4/d6,S9/S27.
TRAIN16 calibrations+16 measured P=32 executions. Freeze all templates before
ANY held-out execution. HELD16 conditions on EACH P/F:32 calibrations+32 measured
=64 executions. Additional held controls seed331,d4,ORDER/NEG,P/F with own
calibration:8 executions. No selected seed replaces any other. Same fixed
calibration/training/held partitions in every readout. No pilot data enters fitting.

## External readouts and falsification

At EACH distance separately, unscaled Euclidean nearest class mean from four
training seeds. Class0=S9,class1=S27. No normalization, whitening, feature choice,
phase alignment, seed metadata, palette or virgin subtraction. Freeze10 models:
5 preregistered representations x2 distances; no best-model selection.
SIGNED primary: final48 sensory banks q/wx/wy/wz/power/dqdt at all3 taus:18.
ENERGY secondary: final48 energy-density banks:3.
ALL_TRACE secondary: all405 final components, tau-major [7global,64H,64C].
INSTANT secondary: receiver final48 all64 u/v:128.
QR10_STYLE secondary: receiver u/v times4..24 every.2:12928, identical FEATURE
RECIPE to QR10, now applied to new matched-work triple-exposure inputs; not a
retroactive rerun/relabel of QR10's historical nine failed models.
Templates/labels remain external, never installed into any neuron.

Per model held-out gate>=7/8 correct BOTH P/F, no ties, predictions identical,
all relevant validity gates; pairwise same-seed S9/S27 norm separation>1e-8
and>=5*max grid error, each feature refinement<=10%. Tie if distance difference
<=1e-12*max(distances,1e-30), counted incorrect. Below floor FAIL; numerical
invalidity INDETERMINATE; valid incorrect FAIL. Preserve every train/held error
and ambiguity. Report within-seed differences and between-seed within-label RMS
separately, no population significance or autonomous recognition claim.
ORDER,NEG,SINGLE pilot/held controls report within-seed differences and signed/
energy-only behavior separately, not extra decoder classes. Main identity failure
does not negate resolved within-seed structure. No information performance claim
from dimensionality or an externally decoded temporary history.

## Conditional morphology, reset and retention

Candidate histogram-preserving local swaps borrow QR6 constraints, NEW scores:
S_m=H_tau8,m+.5*abs(C_tau8,m-C_tau.5,m). At own age48, not already committed,
enabled flag: eligible unequal-color cardinal edges, both endpoints H_tau8>=.01,
both S>=.01, at least one S>=.05*Smax. Rank descending score sum then ascending
(m,n). Greedily select at most4 module-disjoint edges and swap OLD palette values
synchronously. No minimum count, no label/desired shape or per-role special case.
One externally bounded commitment after repeated exposure, not autonomous
continuous morphogenesis. Record every score, eligibility/rank, accepted/rejected
edge, actual edits and pre/post energy. Colors0..4, histogram unchanged, <=8 positions.
u/v/traces unchanged by commit, coefficients rebuilt, switch work=Epost-Epre.

Loading an authentic end48 bounded neuron checkpoint for this gated operation is
state continuation, not replaying CSV history to construct neuron memory. No field
trajectory is invented by that operation. Fluid end state is an explicit unchanged
reference; only actual neuron state changes. Source/receiver follow identical law.

L4 pilot operates on the recorded P/F end states for S9,S27,ORDER,NEG,SINGLE,
QUIET,OFF,TRACES_OFF,SCRAMBLED; FROZEN evaluates S9 eligibility but commits0.
Receiver eligibility and numerical consistency gate L5: at least one exposed
receiver edit, quiet/OFF/trace-off receiver edits0, legal bound/histogram, exact
repeat, switch-work identity, P/F receiver edit Jaccard>=.90 for S9/S27/ORDER
(union0 defined1), actual P equality/differences retained. Numerical discrepancy
makes L4 INDETERMINATE, zero exposure-dependent edits FAIL. Source edits and their
refinement are separately reported, not hidden, but source is restored before
receiver-specific retention testing. Compare SINGLE and different structure;
no automatic claim edits encode source identity or repetition necessity.

L5 pilot: twelve retained receiver variants S9,S27,ORDER,NEG,SINGLE,QUIET,OFF,
TRACES_OFF,SCRAMBLED,FROZEN,RESTORED_S9,VIRGIN on EACH P/F =>24 probe runs,
plus2 virgin probe-work calibrations=26 physics executions. For EVERY probe,
source palette restored to original, preserve ONLY declared receiver palette;
reset fluid q/w, ALL neuron u/v/sensor packets/previous-q,405 traces, age,
commit flags and ALL work/loss/port accounts exactly0. Record removed physical
energy at reset; do not claim reset conserves energy. No hidden history/template
or class metadata survives. Original palette backups are external apparatus.
Probe is same source9 MID pulse0..8, envelope sin(pi*t/8)^2,horizon16. Its force
amplitude comes from independent VIRGIN probe net-work1 calibration per seed/d/grid,
then remains IDENTICAL for all retained variants. Actual supplied work may vary
with feedback; require <=1% difference from virgin, never rescale outcomes.

L5 causal pilot requires S9/S27 adapted-vs-virgin receiver full u/v history
relative difference>=1%, absolute norm>1e-8 on BOTH grids, deltafine norm>=5x
norm(deltacoarse-deltafine), frozen/quiet/trace-off/restored match virgin within
1e-12 relative, all physical/structural validity. SCRAMBLED and ORDER contrasts
reported separately as experience-specificity questions; different alone not useful.
If L4/L5 mandatory pilot fails, stop dependent retention extension, retain evidence.

If pilot passes, apply SAME commitment to48 actual TRAIN/HELD identity end states
and4 additional held structure states (52 operations, not new simulations).
L5 extension primary all8seeds*d4/d6*2history*2variants[ADAPTED,VIRGIN]=64 probes;
fine ALL4held*2d*2history*2variants=32 probes. Independent virgin probe calibrations
16primary+8fine=24. Total120 new physical executions. No reuses invented as runs.
Four training seeds freeze2 retained-response class means per distance BEFORE
held retention probes: receiver u/v times4..16 every.2,7808 numeric components.
Compare adapted and virgin using registered raw means separately; held same
>=7/8,uncertainty,stability gates. Improvement requires valid adapted PASS and
more correct held cases than virgin on BOTH grids, not just larger response.
Persistent response modification, exposure specificity and usefulness independent.

## Evidence, resources, stopping and delivery

Maximum physical matrix13+35+32+64+8+26+120=298 executions. Commitment operations
and reset/restore inspections have separate ledger kinds, never counted as PDE
runs. Full prior-stage cases remain retained if later stages gate off. Exact plan,
STARTED/COMPLETE/FAILED/NOT_RUN and reasons written before every stage; refuse
existing output directories. Record calibration associations, freeze timing,
source commit/compiler/executable/input hashes before execution. No outcome tuning.
Benchmark L1 then pilot and forecast remaining work before main/retention stages.
Ceilings60min physical case wall time,16GB raw case data; stop dependent expansion
if forecast exceeds either, report NOT RUN. No scale to4096, movement or collisions.

Versioned QR11 fluid fields plus owned neuron/local-packet/trace binary stream
EVERY ACTUAL TICK, full palette/reset/commit state and source/force/energy CSVs.
Full fluid0,16,32,48 for measured exposures,0/end for calibrations; L1/probes0,
half,end. Export full P and all64 signed u/v,405 traces per neuron at checkpoints.
Independent Python reconstructs local sensors at fields, ALL trace updates from
actual packets/own u/v, exact kicks/exchange/energy, calibrated amplitudes, edits,
reset invariants, numerical restrictions, templates/predictions and every gate.
No stored Rust PASS flags substitute for verification. Energy audit math.fsum.
SHA256 manifests and complete viewer-free review/full-field packages outside Git;
fresh extraction rebuild/audit and preserve all errors/NOT_RUN. Scientific figures
for sensors, traces, magnitude/sign controls, refinement, morphology and retention
where executed; unexecuted figures explicitly marked, no synthetic scientific data.
Run README severe Rust/Python and isolated viewer checks, verify historical hashes,
inspect target/diff/staged checks, update README/HANDOFF/index/new measured report,
commit/push,verify remote SHA and exact hosted CI separately. No viewer/native FPS
claim or iGPU preference change. Answer all8 directive questions with recorded
artifact references. A completed negative experiment is not a reason to refit.
