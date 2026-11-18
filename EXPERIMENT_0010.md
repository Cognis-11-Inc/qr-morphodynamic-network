# Experiment 0010: numerical rehabilitation and controlled neural-fluid coupling

Registered 2026-11-18 against clean main457c2f9. This separate commit precedes
implementation and outcome collection. QR9 remains FAIL; QR8 results and all
historical scientific sources remain unchanged, bound by the protected manifest.
Serial CPU f64 only. No plasticity, mobile geometry, learning or memory claim.
Principle 002 is a proposed mechanism, not an experimentally established law.

## Frozen numerical protocol

Retain QR9 equations, rigid walls, fourth-order staggered gradient/negative
transpose divergence and symmetric second-order time split, domain24 cubed,
normalized sound speed1 and QR9 engineered physical mapping. Copy the solver to
a separate QR10 module; change reporting sums to deterministic Neumaier summation.
No clipping, normalization during integration, hidden energy correction or filters.
Python math.fsum of independently decoded squared f64 fields is the accounting
reference. Compare naive/compensated sums, actual energy drift and energy balance
separately; squared-term rounding remains part of the explicit error budget.
Accounting relative tolerance1e-12 is RETAINED: roughly4500 machine epsilons,
well above compensated accumulation and multiplication roundoff. Record absolute
errors too. Gaussian unit-energy initialization is explicit, once only.

Four modes (4,0,0),(6,0,0),(8,0,0),(4,4,4), each on
(N,dt)=(24,.0125),(48,.05),(48,.025),(48,.0125),(96,.0125).
Horizon24; full fields at0,6,12,24; energy and projections every tick.
Gaussian on48/.05,48/.025,96/.0125; ZERO48/.05;
HIGH48/.05 independent byte repeat; HIGH48/.05 long horizon240 with
checkpoints0,60,120,240. Total26 executions. Gaussian every-tick axes probes
at signed offsets0,2,4,6 retained. Exact wall slots, finiteness, reproducibility,
Gaussian reflection/permutation energy symmetry relative1e-10 are required.
N24 is a spatial-rate diagnostic, excluded from primary physical-accuracy gates.

A physical accuracy: full combined pressure/velocity relative L2 <=1% on N48,
<=.15% on N96; absolute RMS reported, pressure and velocity errors separately
with combined-reference denominator to avoid zero-component singularities.
Modal phase <=.015rad, amplitude error<=.003, relative phase-derived speed error
<=.003 on N48/96 through24. These budgets exceed known QR9 absolute errors
without altering its original verdict; they bound exploratory field uncertainty,
not high precision efficiency. Long240 is reliability/energy only, not physical
accuracy over that horizon. Gaussian has no point-source analytical gate.

B temporal convergence: FIX N48, compare full fields to exact semidiscrete
standing waves on dt .05,.025,.0125. Across nonzero checkpoints maximum errors
must have successive ratios .20..30 (expected second order, ideal.25).
If coarse error<1e-10 report rate INDETERMINATE, not failure or invented order.

C spatial convergence: FIX dt.0125 on24/48/96. Report raw continuum errors and
their ratios without imposing monotonicity on cancellation-prone totals.
Independently derive staggered eigenfrequency kh; remove ONLY the analytically
predicted time-discretization field error for the spatial diagnostic, never
correct stored observations. Compare corrected fields with continuum: successive
maximum error ratios .04..09 (fourth order ideal.0625). Also report exact
semidiscrete-to-continuum errors and correction residual against exact split
solution<=1e-10 relative. Failure remains attached, not hidden by accuracy.

D conservation: all-tick actual co-timed energy drift<=.3% on primary48,
<=.1% on96; long240<=.3%. No source work for standalone fixtures.
Every checkpoint compensated energy versus fsum <=1e-12 relative, partition
sum<=1e-12. Report actual drift separately from reporting error and roundoff.
E reliability: all state finite, wall slots exactly0, ZERO exactly0, independent
repeat bytes identical, symmetries as above, analytical split agreement1e-10.

LEVEL A requires A,D,E, including accounting; B/C order limitations do not block
the pilot. LEVEL B requires A..E. No global success score. A failure stops before
coupled matrix. Questions receive PASS/FAIL/INDETERMINATE; unexecuted work NOT RUN.

## Lawful stationary neural adapter and pilot

Two actual independently configured 8x8 QR neurons, palettes obtained from the
unchanged Lattice initializer IDs2182/2186 at each registered seed. Reimplement
QR6 omega/gamma/cardinal internal edge equations and exact half damping / Verlet /
half damping with mass1, frozen palettes. External graph edges disabled in FLUID;
this is an isolated-neuron adapter, not the full4096 population. Test coefficient
and short trajectory parity against the isolated equations independently.
No QR6 force-cache reuse after external kicks. Source position(10.5,12.5,12.5),
receiver source+(d,0,0). Engineered reciprocal transducer beta=.1 at BOTH9/27:
qdot_i=beta W_i v/h^3; vdot=-beta sum W_i q_i.
W is normalized tensor hat, width1.5m (resolved by3 primary cells/radius).
Exact rotation of neural velocity and kernel pressure projection; ascending
ports then reversed half sweeps around independent fluid/neuron steps.
No coupling potential energy; exchange kinetic/fluid energy must cancel.
Track individual port fluid/neural work, external kicks, damping and total balance.
Direct comparison adds spring .4/6 between matching modules of the two neurons;
this artificial direct link is not a historical distance-d graph comparison.

Pilot seed211 LOW omega2pi/12, d2, source9 and27 separately, unit amplitude
external force sin(omega*t)*sin(pi*t/12)^2 through12, zero thereafter, horizon24.
Force uses midpoint kick half before/after free steps, exact kick work recorded.
No equal-work rescaling: report actual work and emission per work explicitly.
Both labels on48/.05,48/.025,96/.025. Primary controls per label:
ZERO; OFF (both ports disabled); FROZEN (source remains u=v=0, force disabled);
SOURCE_ONLY (receiver transducer disabled); RECEIVER_ONLY (source disabled);
DIRECT (fluid ports off, direct spring on). Independent primary S9 repeat.
Total19 cases (6 base +12 controls +1 repeat).
Full fluid plus every module u/v and palette at0,12,24. All-tick metrics and
remote64-module signed u/v at every.1; source excluded from readout.

C1 emission PASS when peak fluid energy >1e-10 supplied work and source-port
positive transfer>1e-10 work, work>0. C2 reception PASS when receiver peak
mechanical energy>1e-10 work and OFF/RECEIVER_ONLY/ZERO/FROZEN remote state
exactly0. C3 reciprocal exchange cancellation <=1e-12 relative to max(initial
energy, absolute cumulative exchange, work,1e-30), combined energy+loss-work
residual<=1% max positive cumulative work. Report per-port backflow separately.
C7 controls require exact0 where specified, frozen palettes and repeat bytes.
Pilot extension gate additionally requires remote full u/v time-series relative
refinement<=10% for both temporal and spatial grids and both labels; source work
relative difference<=2%. This is a pilot uncertainty gate, not Level B accuracy.
Invalid refinement makes stronger claims INDETERMINATE, never suppressing causal
observations. Stop extended matrix if this gate fails.

## Conditional extended matrix, information and interference

Only after valid pilot within budget: seeds211,223 calibration and227,229 held,
bands LOW/MID/HIGH=2pi/(12,8,6), d2,4,6, labels9/27, primary48/.05:
72 logical cases, with pilot211/LOW/d2 reused explicitly (70 new executions).
Fit18 two-class nearest-mean templates using ONLY two calibration seeds, all
remote u/v samples time4..24 every.2, order time/module/u,v; no preprocessing,
source samples, metadata, alignment, selection or refit. Freeze templates before
held-out execution. Repeat36 held cases on96/.025 (primary spatial+temporal
uncertainty check); no4096 scaling in this registration.
C4 perband/distance:4/4 correct on both grids, ties incorrect (relative distance
gap<=1e-12), numeric class separation>1e-8 and>=5x grid discrepancy; remote
features refinement<=10%. Invalid uncertainty INDETERMINATE; valid incorrect FAIL.
Preserve every prediction/margin including wrong/tied cases. C5 report receiver
peak/work and peak/emitted positive work, arrival above1e-10 work, fluid probes,
actual signed spectra; a band/distance difference only quantitative when Level B
and >5x refinement uncertainty. No assumed frequency ranking or material loss.

C6 extended interference seed211 LOW d4: add third actual neuron at
(10.5,14.5,12.5), original source9 and second source9, identical force amplitude.
Execute A-only,B-only,AB+,AB- at48/.05 and96/.025 (8 cases).
Signed full fields and receiver histories AB± vs A±B relative<=1e-10;
report signed reinforcement/cancellation and energy cross terms, no energy sums
as interference proof. C6 NOT RUN if extension blocked.

## Resources, provenance and delivery

Serial execution budget30min physics, total raw storage8GB; benchmark standalone
before pilot and pilot before extension. No seed substitution or parameter tuning.
Refuse existing case folders, full plan/events/completion ledger, preserve errors.
Before execution commit implementation and record executable SHA/compiler/source
hashes and frozen registration SHA. QR10AC01 schema1 follows QR9 layout with new
magic; neural arrays/palette and metadata stored alongside each checkpoint.
CSV all-tick diagnostics, independent NumPy analytical fields and math.fsum audit.
Integrity SHA256 manifest, portable review and full-field archives outside Git;
fresh extraction must reproduce audit. Plot recorded errors/rates/energy and,
when run, remote propagation/discrimination (NOT RUN plot if gated).
Update results, README, HANDOFF,index, local strict Rust/Python/viewer checks;
inspect diff/staged check, commit,push,verify remote SHA and hosted CI separately.
No prior failed evidence is overwritten. Unexpected diagnosis is post-outcome.
