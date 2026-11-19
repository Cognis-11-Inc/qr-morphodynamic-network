# Experiment 0012: the morphodynamic network

Preregistered 2026-11-19 against main52e4dba, after the authorized branding-only
rename of ecfd892. This commit precedes new implementation and outcome evidence.
Project: QR Morphodynamic Network. Organization: Cognis 11 Inc. Verified remote:
https://github.com/Cognis-11-Inc/qr-neural-memory-system (no repository rename).
Historical sources/results are protected by the accompanying SHA256 manifest;
only README,HANDOFF,experiment index and lib exports permit shared additions.
Principle 002 remains a proposed mechanism, not an experimentally established law.
QR11's failed retained discrimination and all prior failures remain unchanged.
No learning, memory, recognition, intelligence, emergence or business-success gate.

## Questions and separate dependencies

A validates extended physical integration; B tests ongoing local morphology;
C tests a single event's causal effect; D tests collective dynamics; E tests a
compositional description; F assesses exploitation. Each scientific question
receives PASS/FAIL/INDETERMINATE, not one global success score. Missing dependent
conditions are NOT RUN, never negative measurements. No outcome-dependent seed,
threshold, representation, geometry, intervention or timing replacement is allowed.
B/C/D require A's physical validity. C and D require B's physical/numerical event
validity, not a favorable diversity or memory result. C additionally requires the
specified source event to be eligible. E mathematical work is independent; its
physical prediction test requires A, independently of B/C/D outcomes. F always
reports actual evidence and missing work. Diagnostics after failures are labelled
post-outcome and never revise the original gates.

## Physical configuration and typed boundaries

Serial CPU f64, unchanged acoustic_0010 Fluid, normalized domain[0,24]^3, rigid
reflecting walls, c=1, original fourth-order staggered gradient and negative
transpose divergence, symmetric split. QR10's material mapping is engineered;
no implemented seawater absorption, biological material, or spontaneous energy.
Copy QR11 isolated Neuron/Port arithmetic into a NEW versioned module; never edit
old physics. Each genuine neuron independently owns palette64u8, u/v64 each,
intrinsic color/shape coefficients, cardinal internal edges, damping, packet7,
previous pressure, local age and bounded405-component trace. Same local code for
all roles; no global statistics, seed/label, other private state or prediction API
inside the neuron/controller. Scientific observer may record the complete system.

SQ geometry: centers(10,10,12),(14,10,12),(10,14,12),(14,14,12), node IDs0..3.
Palette generator IDs2182,2186,2184,2188, unchanged seeded SplitMix initialization.
ALT geometry: (9,9,12),(15,9,12),(9,15,12),(15,15,12), spacing6.
Tensor-hat support radius1.5 in EACH coordinate, normalized weights. SQ nearest
centers4 apart and ALT6: supports have disjoint positive-weight grid indices.
They are resolved at h=.5/.25 (3/6 cells per radius), all centers lie on grid-face
coordinates on both grids, minimum wall clearance7.5. Check sums, index overlap,
centers and wall slots independently; do not assume spherical supports.
Each QR node has reciprocal beta.1 ports at modules9 AND27. Same pressure kernel
for both ports within a node, so order matters: node-major/module9,27 ascending
half rotations, unchanged fluid + intrinsic QR steps, reverse half rotations.
Midpoint external half-kicks before/after; sensors/traces AFTER full physical step,
then morphology decisions, then optional registered perturbation. No direct graph
edges or hidden communication bus. Full fluid has one owner in shared cases.

P=(48,.05), T=(48,.025), F=(96,.025). No parallel physical updates or GPU.
Pulse force: sin(2*pi*t/8)*sin(pi*t/12)^2 for0<=t<=12, then0. Unit amplitude,
N0 module9 only, except declared common/independent controls. Sustained input:
sin(2*pi*t/8)*sin(pi*t/8)^2 through t4, then sin(2*pi*t/8) through horizon40.
Common drive: all4 nodes force amplitude.5; sum of squared applied forces equals
unit single-source forcing, but actual work need not match. Report work rather
than claiming equal energy. There is no decoder or source-work retuning here.

## Numerical and accounting requirements

A fixed morphology horizon24 must agree with original QR11 physical equations
in two-node legacy geometry(10.5,12.5,12.5),(14.5,12.5,12.5): full fields/u/v
relative<=1e-12, same source9 pulse. QR11 runs are actual separate oracle
trajectories, counted separately. Sensors OFF must leave physics byte-identical;
repeat bytes must match; quiet exactly0; coupling OFF has zero fluid and remote
activity, while directly forced N0 can move. All values finite, wall slots0,
|trace|<=1+1e-14. Independently reconstruct local packets at full checkpoints,
all405 online updates, intrinsic QR steps, damping, kicks, rotations and events.
Trace replay maximum absolute error<=1e-12. Actual reporting/accounting errors
<=1e-12 relative to max(cumulative positive input,stored energy,1e-30).

Total residual E+loss-Einitial-Wforce-Wswitch-Wsham-Wperturb must be<=1% of
max(initial energy,cumulative POSITIVE work from ALL external channels,1e-30).
Include negative work separately. No correction, state rescaling except the
explicit sham, hidden forcing, clipping or energy normalization in integration.
Every event's switch work is Eafter-Ebefore at unchanged u/v; independently
rebuild coefficients. Track signed port transfer, backflow, cancellation and per-
node energy; reciprocal exchange error<=1e-12 of positive work/stored energy.
Stop a physical case on nonfinite state, illegal palette, >100 times max(initial
energy,cumulative positive work,1e-20) stored energy, or resource ceiling. Preserve
partial data and FAILED event. Do not turn process completion into scientific PASS.

Compare whole time-aligned histories of signed u/v, packets and all traces across
P/T and P/F; relative L2<=10%, denominator finer norm floor1e-30. Compare full
fluid fields at registered common times, using exact QR11 restriction:8-cell
pressure average, same normal face (fine normal2i+1),4 transverse velocity average.
No phase alignment or state repair. Event sequence timing, node, accepted swaps
and actual palettes must agree EXACTLY across P/T/F for the B gate. A discrete
mismatch gives numerical INDETERMINATE and blocks C/D, even if bounded or pretty.
Report dynamic validity separately from event frequency and changed responses.

## Local repeated morphology law, frozen candidate

Retain QR11 phi scales, tau(.5,2,8), exact ZOH updates,405 components and signed/
quadratic parity. H8=z[277:341], C8=z[341:405], Cfast=z[71:135]. Score per module
S=H8+.5*abs(C8-Cfast). Use only own values/current palette/local clock/history.
A hysteresis latch turns ON when max(H8)>=.02, OFF when max(H8)<.005; otherwise
retains its previous value. Initially OFF. Evaluate latch after each trace step.
Event opportunities at own local times16,24,32 ONLY (bounded local clock,
refractory8, max3 successful events and3 swaps per node). At an opportunity,
require latch ON, own last successful event>=8 units ago, and remaining budget.
Eligible unequal-color cardinal edge(m,n),m<n: H8[m],H8[n]>=.01, S[m],S[n]>=.01,
and at least one endpoint score>=.05*Smax. Rank by descending S[m]+S[n], then
lexicographic(m,n); accept at most ONE edge per event, evaluated on old palette.
No minimum changes; no forced eligibility. Rebuild dynamics at unchanged u/v,
packet,previous pressure,age,traces and loss; record exact switch work. No reset.
No committed-once restriction from QR11: a new local controller owns its latch,
last event, attempt/event/veto counts and budget. Port geometry does not move.

All opportunities log every node's trigger state, scores/eligibility/rank, before/
after palette and work, including quiet, rejected and vetoed proposals. FIXED and
VETO controls run same local observation but veto changes externally. TRACE_OFF
zeros banks; OFF disables ports, not forced N0's own oscillation. NONADAPTIVE
control at16,24,32 chooses lexicographically first unequal cardinal edge on current
palette, without traces; if none, abstains. Same max3 and work accounting. It is
an explicit external intervention, never called adaptive/local learning.

M1 ACTIVITY PASS requires>=2 genuine nodes each with>=2 legal committed events
in the shared pilot, quiet events0, trace-off events0, and no remote OFF events.
Otherwise FAIL when dynamics valid. M1 NUMERICAL VALIDITY is separate, requiring
all physical gates and exact refined event sequence. M1 CONSEQUENCE compares
ADAPTIVE versus VETO_ALL signed histories: norm>1e-8 and fine difference>=5x
norm(deltaP-deltaF); no guarantee of beneficial behavior.

## Exact state, forks and M2 interventions

Full checkpoints include all signed fluid q/w, every palette/u/v, packet,previous,
405 traces,age,loss, local controller state/budget/counters/work, global clock,
geometry, port order/parameters and EVERY energy/work accumulator including
compensation terms. Reconstruct derived coefficients/kernels deterministically
and reject incompatible ABI/grid/units/clock/configuration or checksum. Snapshot
roundtrip must reproduce exact bytes and subsequent actual state, not just u/v.

Save B ADAPTIVE state at16 immediately AFTER physical+sensing update and BEFORE
any opportunity processing. C loads this exact checkpoint on P/F. External force
is0 thereafter. Target is N0's local eligible edge at16; if none, C NOT RUN.
All future morphology is externally vetoed in ALL C continuations. Other nodes'
16-unit changes are vetoed identically. Only target permit/veto and their declared
palette/controller/work consequences differ. Never reset transient or fluid state.
Branch initial checkpoint hashes must equal B ancestry and each other. Compare
post-intervention16,20,24 plus every tick; horizon absolute24 (8-unit continuation).

Six continuations per grid:
PERMIT, VETO, SHAM, EXTERNAL, ISOLATED_PERMIT, ISOLATED_VETO.
SHAM keeps original palette and adds the permit event's EXACT energy change to
N0 kinetic energy: scale all its velocities by sqrt(1+dW/K). Allowed only if K>0
and K+dW>=0; otherwise SHAM NOT RUN and energy attribution INDETERMINATE. This is
a declared external intervention; record before/after and work, never call it
silent normalization. Equal total energy is not equal modal distribution; any
permit/sham contrast has that explicit attribution limitation. EXTERNAL makes
the frozen NONADAPTIVE lexicographic swap in N0 instead. ISOLATED branches disable
ports of N1,N2,N3 identically before the pair's intervention; existing remote
motion persists autonomously. Other remote neural histories must match EXACTLY
between that pair, proving absence of a hidden non-fluid communication path.

M2 activity->morphology PASS: at least one unforced node commits in B shared,
with no such commits in matched OFF/TRACE_OFF/quiet controls. Source changes in
OFF are not fluid-sensing evidence. M2 local/remote influence separately require
signed difference norm>1e-8, remote relative L2 effect>=.001 for>=1 other node,
fine delta norm>=5x norm(deltaP-deltaF), both grids bounded/physically valid,
exact isolated remote equality. Compare SAME physical times; record threshold
onset (difference first exceeds1e-4 its own final peak), spatial reach, per-node
magnitude and fields. This is observed numerical onset, not an assumed continuum
front or proof of useful/chaotic computation. Event-vs-sham and external-change
comparisons use the same numerical separation rule, separately; attribution to
altered coefficients alone remains limited by the sham's modal distribution.

## Frozen stages, seeds and coverage (maximum80 actual trajectories)

A seed401 SQ, horizon24: FIXED P/T/F; QUIET P/F; OFF P/F; SENSOR_OFF P;
independent FIXED repeat P; NEW_LEGACY P/F and ORIGINAL_QR11_ORACLE P/F =13.
The9 population cases use4 neurons;4 parity cases use the stated original2.

B seed401 SQ horizon40: ADAPTIVE P/T/F; ADAPTIVE_QUIET P/F; ADAPTIVE_OFF P/F;
ADAPTIVE_TRACE_OFF P/F; VETO_ALL P/F; independent ADAPTIVE repeat P =12.

C same B checkpoint, six continuations P/F =12. These are actual PDE continuations,
not reused as independent origins; preserve ancestry and count actual work.

D seed409, horizon40, P/F for each: FIXED,ADAPTIVE,OFF,COMMON,NONADAPTIVE,
SUSTAINED_FIXED,SUSTAINED_ADAPTIVE,ALT_FIXED,ALT_ADAPTIVE,SIMPLE,
IND0,IND1,IND2,IND3,SOLO0,PERTURB_FIXED,PERTURB_ADAPTIVE =34.
Seed419 additionally FIXED/ADAPTIVE P/F =4. Total D38.
INDi are ACTUAL single-neuron/private-fluid runs of original node i at its own SQ
position and palette, common forcing amplitude.5. Assemble independent-common
measurements from all4 runs, never pretend they shared one fluid. SOLO0 unit
force plus three exact analytic zero solutions supplies the single-source
independent control; zero solutions are declared analytical, not new executions.
SIMPLE is a separate, frozen, same-fluid baseline with only modules9/27 active,
independent omega1,gamma.1 scalar oscillators, no internal edges, same ports and
forcing. Not a substitute for QR nodes; no spectral fit or equal-response claim.
PERTURB adds impulse+.01 to N1 module9 AFTER morphology at time24. All work is
explicit; compare with the identical-seed unperturbed case, no silent resets.

E seed427, no morphology, horizon8: DIRECT4 P/T/F, DIRECT_PAIR01 P and
DIRECT_PAIR23 P =5. Predict independently BEFORE generating these direct outcomes;
freeze input/model/prediction SHA. Smaller connected pair descriptions are
validated; their PRIVATE full-fluid trajectories are NOT summed to predict4.

A13+B12+C12+D38+E5=80. Plans include every potential condition with initial NOT RUN,
actual STARTED/COMPLETE/FAILED and stopping reason. No unexecuted case counted.
A failure blocks B/C/D and physical E. B event/refinement invalidity blocks C/D,
not independent E. All failure evidence and mathematical E/F remain preserved.

## Collective measures and potency criteria

Every-tick per-node energy, signed u/v, local pressure, port transfers and external
work. Report energy participation (sumE)^2/sumE^2 (0 when quiet), response diversity
1-mean pairwise absolute cosine similarity of node128-state histories (undefined
pairs with norm<1e-8 omitted and count retained), arrival above1e-10 positive work,
peak energy/work and emission, signed module9 v spectra, complex carrier projections
and Hilbert phase-locking over16..40 (undefined if RMS<1e-8). No invented phases for
zero nodes. Report decay E40/E12 for transient forcing, sustained energy history,
geometry dependence, perturbation deltas/onsets and bounded recovery. Do not add
activity magnitudes as signed interference. Instantaneous energy is not an
integrated flow. No assumed synchronization, wider reach or increased diversity.

M3 RECIPROCAL COLLECTIVE EFFECT PASS requires>=2 remote nodes detected, shared vs
independent single-source signed effect>.001 relative and>1e-8 absolute,>=5x grid
uncertainty, OFF/independent analytical remote0. COMMON vs assembled INDi compares
same per-node force, separately controlling externally imposed coordination.
M3 MORPHOLOGICAL MODULATION requires adaptive vs fixed change in at least one
registered scalar(participation,diversity,PLV,decay ratio)>.05 and>=5x combined grid
uncertainty on BOTH standard seeds; undefined observables INDETERMINATE. Every
comparison retains extra event work: activity increase is not energy-free potency.
M3 INCREASED DIVERSITY specifically requires diversity increase>=.05 with5x margin
on both seeds AND relative difference in total positive external work<=1%; otherwise
FAIL or INDETERMINATE if numerically invalid/dose-confounded. Regime separation
(sustained vs transient, ALT vs SQ) uses signed response difference>10%, absolute
>1e-8 and5x grid uncertainty. A driven regime is not autonomous emergence.
Perturbation reach and recovery are separately reported; bounded energy and no
accounting failure required, no guaranteed return to an arbitrary equilibrium time.
Potency here means differentiated, controllable causal dynamics, not intelligence.

## M4 formalism, independent composition prediction and utility

Objects are explicitly typed valid computational-state sets, indexed by grid,
dt, units, face orientation, boundary conditions, port ABI, ownership and split
phase/clock. Morphisms are deterministic PARTIAL maps with declared preconditions
and a target type; nonfinite/illegal/incompatible transitions are undefined.
Identity is empty execution; composition is sequential application on the domain
where both maps are defined. Prove closure, identity and associativity as partial
functions/relations. Floating arithmetic is NOT algebraically reassociated:
parenthesization preserves the identical ordered operator word. A path category
alone is valid but potentially trivial and earns no predictive utility by itself.

Open components: own QR state + two current fluid port projections; outputs are
updated own state and the weighted fluid pressure increment. Two node-pair modules
expose shared fluid interfaces. Binding identifies ONE shared fluid register, with
all kernels and fixed ascending/reverse rotation order; fluid evolution runs once.
No tensor product of closed private-fluid neuron trajectories. Independent Python
constructs intrinsic node maps, reciprocal port rotations and staggered fluid map
from equations/initial palettes/registered input, not direct-run outputs. It composes
these descriptions, predicting complete4-node state/field checkpoints at0,4,8 on
P/T/F and the2-node P pairs. Record input/prediction hashes before E direct runs.
This is an independently implemented open-operator model, not a new physical law
or proven general decorated-cospan functor. Do not assert unrestricted gluing,
commuting port operators, arbitrary reconfiguration or reduced-state Markov closure.

MATHEMATICAL VALIDITY PASS requires precise domains/codomains and partial-map proof,
exact identity and associative-word tests, lawful compilation and constraint rejection.
PHYSICAL AGREEMENT PASS requires independent composed/direct full fields and neural
states relative<=1e-10 at all nonzero checkpoints and both pairs, every physical E
case valid, P/T/F direct comparisons<=10%. PREDICTIVE UTILITY additionally requires
remote predicted norm>1e-10 and combined prediction error<=.1 times error of a
registered noncategorical CLOSED-product baseline (independent QR neurons/fluids,
remote state0 under N0-only forcing). The baseline tests missing interfaces, not
whether category notation is intrinsically superior to ordinary modular modeling.
ENGINEERING UTILITY requires accepted valid replacements, all6 invalid interfaces
rejected (grid,dt,units,face orientation,duplicate-fluid ownership,missing-node port),
and>=1 additional physically invalid configuration caught beyond a straightforward
noncategorical validator checking the SAME physical constraints. If benefits equal,
FAIL for demonstrated categorical advantage, even with a mathematically valid model.
Report construction/validation/runtime costs and module replacement tests, not a
manufactured code-saving or speed advantage. Mathematical success is independent
of M1-M3. Sources motivate open interfaces, not proof QR mechanics is categorical:
Baez/Pollard, https://arxiv.org/abs/1704.02051 ;
Baez/Courser/Vasilakopoulou, https://arxiv.org/abs/2101.09363 .

## Resources, observability, independent review and delivery

Prior empirical benchmark: QR11's registered N96/.025 48-unit cases ~40s and
16-unit probes ~13.6s, P48/.05 48-unit ~2.6s, actual records preserved in
results/experiment_0011. These are OLD benchmarks, not new QR12 outcome evidence.
Conservative forecast doubles duration-scaled old rates for extra bodies and IO;
maximum80 trajectories within3600 physical-case seconds and16GB raw. Hard per-case
300s; physics RSS4GB; independent analysis<=8GB; no population4096 or GPU scaling.
Record exact quantitative forecast from A before B and from B before C/D, including
fields/observations/branches and15% remaining margin; if either ceiling exceeded,
stop expansion and mark dependent cases NOT RUN. Analysis/packaging time is separate.

Versioned full snapshots and every-tick OWNED signed node/trace/controller stream;
full fluid at A0,12,24; B/D0,16,24,32,40 with complete PRE-event snapshots16,24,32;
C before/after intervention16,20,24; E0,4,8. Retain kicks, every port rotation,
all event causes, input/work/dissipation/switch ledgers, full configuration and
branch ancestry. Exact binary schema documented before execution. Never substitute
synthetic viewer data. No viewer runtime needed; existing viewer only strict checks.

Rust is authoritative physics/state/events/serial executor. Python independently
audits raw numerical state, all online trace updates, QR steps, local laws, palette
and work changes, branch ancestry, refinement, observables, formal-interface tests
and predictions. Exact complete-state replay/serialization tests, event no-op and
energy-work controls required. Commit implementation and pre-execution provenance
(executable/compiler/source/input hashes); no code/threshold tuning after outcomes.
Source-freeze archives distinguish actual engine from final delivery source.

Deliver separate results and evidence-based exploitation assessment covering
publication, engine, games/agents, developer toolkit and potential IP. For each:
actual evidence, fair baseline, measured pros/cons, missing validation, prospective
user, smallest demonstrator, clearly estimated effort and pursue/investigate/defer.
No novelty, patentability, exclusivity, legal advice, private material or market
advantage invented from a public research repository. No proprietary publication.
Seven/eight actual-data figures cover activity, morphology, fluid, energy, causal
branches, spectra/synchrony and composition; gated stages explicitly NOT RUN.
Portable review/full-evidence archives, member/raw/source SHA, fresh extraction
rebuild/re-audit, local strict checks, updated README/HANDOFF/index, inspected diff,
commit/push to verified Cognis11 remote, exact remote SHA and hosted CI separately.
