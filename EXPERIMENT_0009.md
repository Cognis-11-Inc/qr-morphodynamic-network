# Experiment 0009: saline acoustic container

Registered 2026-11-15 before implementation or new experimental observations.
Baseline main5fd2794, clean. This file's separate commit freezes the protocol.
No pilot outcomes, calibration outcomes or new-seed measurements exist at freeze.
All earlier experiments remain unchanged. Principle 002 is a proposed mechanism,
not an experimentally established law. No learning or mobility is implemented.

## Stage order and stopping rule

First implement and independently verify the standalone fluid (S1). Only if ALL
registered standalone gates pass may the immersed QR population be implemented
and executed. Then validate reciprocal coupling (S2) before the neural matrix.
If either prerequisite fails, STOP: preserve failures, report downstream questions
INDETERMINATE, deliver the implemented stage and raw evidence. Do not tune the
registration, substitute a solver or collect attractive invalid neural outputs.
Code and independent measurement methods must be committed before each execution.
Analytic unit tests use synthetic fields; numerical validation is separately
labelled. Work-normalization calibration below is explicit, not held-out evidence.

## Reference seawater and limits

Homogeneous stationary reference-composition seawater-like saline liquid, T20 C,
S35 g/kg, atmospheric pressure0.101325 MPa, reference depth0. No flow, gradients,
thermal evolution, chemistry, electrical/ionic signalling or gravity calculation.
This is not pure NaCl solution. No real QR-cell membrane/material is asserted.

Density uses the atmospheric Sharqawy2010 correlation (MIT seawater library
SW_Density, retrieved2026-11-15), T in Celsius, s=S/1000:

    rho=999.92293295+.020341179217*T-.0061624591598*T²
        +.000022614664708*T³-.000000046570659168*T⁴
        +s*(802.00240891-2.0005183488*T+.016771024982*T²
        -.000030600536746*T³)-.000016132224742*s²*T²

Sound speed uses Mackenzie1981, as reproduced by NPL, T Celsius, S ppt, D metres:

    c=1448.96+4.591T-.05304T²+.0002374T³+1.340(S-35)
      +.01630D+.0000001675D²-.01025T(S-35)-7.139e-13*T*D³

Here S35 is the engineering nominal salinity in both correlations; their historical
salinity/temperature scales differ. No metrological TEOS-10 equivalence is claimed.
Mackenzie domain: T2..30, S25..40,D0..8000. K=rho*c² is adiabatic bulk modulus.
Viscosity is documented, NOT an enabled damping approximation:

    mu_w=4.2844324477e-5+1/(.15700386464*(T+64.992620050)²-91.296496657)
    mu=mu_w*(1+(1.540913604+.019981117208*T-.000095203865864*T²)*s
               +(7.9739318223-.075614568881*T+.00047237011074*T²)*s²)

MIT Sharqawy Eq22/23 validity T0..180,S0..150g/kg, atmospheric pressure; stated
viscosity accuracy1.5%. Density fit stated about0.1%, not a measured value here.
Away from reference conditions recompute correlations; not universal constants.
Pressure dependence is NOT extrapolated from the atmospheric density/viscosity
fit; Mackenzie uses depth as its pressure-related proxy. No pressure sweep.

Sources, read before freeze:

- [MIT seawater library and original papers](https://web.mit.edu/seawater/)
- [Sharqawy et al.2010, corrected correlation tables](https://web.mit.edu/lienhard/www/papers/journal/Thermophysical_properties_of_seawater-DWT-16-354-2010.pdf)
- [NPL sound-speed guide](https://resource.npl.co.uk/acoustics/techguides/soundseawater/index.html)
- [NPL-authored archived equation sheet, p1](https://www.comm-tec.com/library/technical_papers/speedsw.pdf)
- [ITTC2011 properties, reference-pressure and salinity distinctions](https://ittc.info/media/4048/75-02-01-03.pdf)
- [NPL absorption mechanisms](https://resource.npl.co.uk/acoustics/techguides/seaabsorption/physics.html)

NPL live equation/absorption pages had TLS/fetch failures; its sound equation was
verified from the NPL-authored PDF. MIT official property source ZIP was read.
Real seawater absorption includes chemical relaxation (boric acid, magnesium
sulfate) as well as pure-water mechanisms. The primary solver is CONSERVATIVE:
viscous, thermal and chemical material absorption are all0 by model choice.
Material frequency-absorption validation is NOT RUN, deferred to a new experiment.
Geometric spreading, interference, transducer response and numerical dispersion
may vary with frequency; none is labelled measured seawater absorption.

## Units and dimensional mapping

L*=1m; t*=L*/c seconds; one QR oscillator module mass M*=1kg;
displacement U*=1e-6m; energy E*=M*U*²/t*² joules. These are ENGINEERED mapping
assumptions, not measured QR materials. u_phys=U*u, velocity=U*/t* v;
QR omega_phys=omega/t*, gamma_phys=gamma/t*, stiffness_phys=M*/t*² k.
QR frequency in Hz is omega/(2pi*t*), morphology-dependent. Pressure scale
p*=sqrt(K*E*/L*³), fluid velocity scale=sqrt(E*/(rho*L*³)).
Normalized acoustic q=p/p*, w=v_fluid/v*, c'=1; fluid E/E*=h³/2 sum(q²+|w|²).

Domain [0,24m]³. Neuron coordinates explicitly (4.5+x,4.5+y,4.5+z)m for
historical x,y,z0..15, ID only an external index. All4096 own independent8x8
palettes and u/v64. Orientation quaternion(1,0,0,0), fixed. Separation1m.
No movement/collision/advection/buoyancy. Fluid API accepts physical coordinates
and grid size, has no Cubic6 dependency; future motion needs new work accounting.

## Standalone fluid discretization

Small linear acoustics: qdot=-div(w), wdot=-grad(q). Cell-centred pressure;
face-normal velocities, x-fast arrays with N³ entries per component. Positive
outer face slots are identically0; negative wall faces implicit0. Closed rigid
reflecting walls, no boundary outflow/absorption. Not an open-ocean model.
Fourth-order staggered derivative at each interior face i+1/2:

    Gq=[(9/8)(q_i+1-q_i)-(1/24)(q_i+2-q_i-1)]/h

Mirror pressure ghosts (q_-1=q_0,q_N=q_N-1); independent per axis. Divergence
is EXACTLY -G transpose, including wall contributions. This gives the semidiscrete
quadratic energy identity. Serial f64 split: q += dt/2 G^T w;
w -= dt G q; q += dt/2 G^T w. States are co-timed, no half-time energy mixing.
This is second order in time, fourth-order interior space, no clipping/filters.
Conservative sufficient CFL: dt*sqrt(3)*(7/6)/h <=1 (spectral upper bound).
Primary N48,h.5m,dt.05; temporal N48,.025; spatial N96,h.25m,dt.025.
T24 (24/c seconds). LOW/MID/HIGH omega=2pi/(12,8,6) normalized,
frequencies=c/(12,8,6)Hz. 2,3,4 wavelengths/domain; minimum12/24 gridpoints
per wavelength and120/240 samples per shortest period. Peaks above these bands
from short pulses must be disclosed; no assertion that all pulse frequencies
are resolved. Source kernel is finite, spatial refinement keeps its metre width.

### Frozen standalone matrix: 17 executions

Each of five fixtures on all3 grids =15: cosine modes (4,0,0),(6,0,0),(8,0,0),
(4,4,4), and isotropic Gaussian exp(-r²/(2*.75²)) centred(12,12,12)m.
Cosine q=product cos(m_axis*pi*x_axis/24), w=0 initially. Gaussian scaled to
actual discrete E=1. Modes left at amplitude1 (known exact continuum energy).
One ZERO on primary; one independent repeat of primary(8,0,0): total17.
Checkpoints0,6,12,24 full q/w. Every tick energy, maxima, modal projections;
fixed signed fluid probes at centre and +/-2,+/-4,+/-6 along each axis.
All case identities/numerical grids recorded. Gaussian probes use cell sampling
at predefined positions, report actual sample coordinates; no interpolation claim.

Python independently reconstructs full energy, exact standing-wave q and face w
(normal component k_axis/|k| * sin(k_axis*x_face) * other cos * sin(|k|t)),
wall slots0, full relative field errors, phase/amplitude/frequency, and projections.
Gate every modal nonzero checkpoint: primary full unaligned relative L2<=5%,
spatial-fine<=1.5%; temporal refinement reduces analytic error attributable to
time (comparison to exact SEMIDISCRETE mode) by factor<=.35 when coarse>1e-8.
Semidiscrete frequency uses k_h=2/h*(9/8*sin(kh/2)-1/24*sin(3kh/2)); same
analytic mode, exact time evolution. Full continuum comparison remains separate.
Measured modal phase error<=.03rad primary,.01 fine; amplitude error<=1% all;
phase-derived effective wave speed error<=1% primary,.25% fine. Near zero phase
use full u/v field norm rather than dividing by instantaneous pressure.
Maximum actual fluid energy drift<=1% primary/temporal,<=.25% spatial-fine,
all ticks (not modified-energy-only evidence). Reconstructed checkpoint energy
relative1e-12; positive wall velocity exact0; ZERO exact0; repeat all raw bytes
identical. Gaussian permutations/reflections of full energy density must agree
relative1e-10; Gaussian drift uses same bound. Spatial refinement must reduce each
modal maximum continuum error by<=.35 when primary>1e-6. Independent Python
replays one small synthetic step to test transpose/closure, not a second full
solver integration. Gaussian arrival/spectrum/spreading are diagnostics, not an
analytic point-source solution. No information verdict inferred from these waves.
All required tests must pass for S1; a single failure stops neural work.

## Conditional immersed model (only after S1)

New dedicated module copies QR6 coefficient equations, palette initializer,
internal cardinal edges, intrinsic damping and synchronous split updates without
editing historical source. External graph edges enabled only DIRECT/HYBRID.
DIRECT fluid coupling0; FLUID external QR edges0; HYBRID both; DECOUPLED both0.
No neural sponge, histories or plasticity. Fluid exists initially zero in all.

Engineered monopole pressure/QR-velocity transducer at every neuron, modules9,27,
same fixed coefficient beta=.1 for both. Kernel tensor hat product
phi=product max(0,1-|x-position|/.75m), at pressure centres; W=phi/sum(phi).
Same kernel for sampling and deposition, sumW=1, fixed physical width .75m.
qdot_i += beta*W_i*v_module/h³; vdot_module -= beta*sum W_i*q_i.
Physical effective area A=beta*sqrt(M*L*/rho) m². Fluid volume source A*xdot,
neural pressure force -A*interpolated p. No additional stored coupling energy;
exchange cancels in E_neural+E_fluid. Morphology changes omega/gamma/QR links,
not this fixed engineered area. Freeze P throughout.
Integrate each transducer exactly as a rotation between neural v and normalized
kernel pressure projection; ordered forward/reverse half-sweeps for symmetric
splitting around separate fluid and QR steps. Record both actual energy changes
and their cancellation. S2 minimal mass1 oscillator plus full fluid fixture on
all3 grids: nonzero energy exchange both ways, relative exchange cancellation
<=1e-12 and combined energy+loss-work residual<=1%, fine<=.25%; full refinement
<=5%/1.5%. Only then full population. Retain raw fields for independent remeasure.

## Conditional finite neural matrix and readouts

Reference seeds211,223; held227,229. Unchanged heterogeneous initializer including
historical module27 policy. Source2182=(10.5,12.5,12.5)m. Primary positive S9/S27
4configurations*3bands*2modules*4seeds=96 runs. All48 held-out repeated on EACH
temporal and spatial grid=96 additional. Negative S9/S27 held primary48 runs;
ZERO seed227 all4 configurations/all3grids (bandLOW metadata only)=12; one raw
repeat reference211/FLUID/LOW/S9 primary=1. Actual scientific253 runs.
Before each192 positive case, independently integrate unit-force calibration
same configuration/seed/grid/band/module; preserve192 separate calibration runs.
Linear force scaling amplitude=sqrt(1/net unit source work) then rerun fresh:
target total external source work1E*, relative tolerance1e-10. Calibration must
have positive work. Negative controls use actual matched positive amplitudes.
Total445 full-population executions if prerequisites pass; never alias cases.
Force=a*sin(omega*t)*sin(pi*t/12)² for0<=t<=12, zero later; identical envelope
policy, sample midpoint each step. Exact discrete force-kick work is recorded.
Finite bandwidth and emitted fluid/QR spectra retained, no perpetual forcing.
Equal net work is NOT equal radiated energy; compare emission and efficiency.

Receivers fixed +x and +y axis offsets2,4,6m from source (IDs derived from
explicit coordinates), two probes per distance. All exclude source. Report
Euclidean metres and equivalent historical hops separately. Sample every.1
normalized time0..24: pressure, three co-timed face-averaged velocities,
local fluid energy, u/v at modules9,27,10,18, whole-neuron mechanical energy.
Feature windows [4,24], every.2: 101samples*2positions per distance.
A fluid-only: q,wx,wy,wz (808); B neuron-only: u/v of4modules (1616);
C combined A+B (2424); D fluid energy-only (202). All normalized physical scales
above fixed globally, never per-frame/per-case. No metadata in numeric features.
Source/receiver histories and complete fields at0,12,24. Mechanical neuron
half-edge energy and full fluid energy reconstructed independently in Python.
Radiated energy is cumulative signed transducer work INTO fluid, not stored fluid
energy at a late time; backflow separate. Net fluid work equals stored fluid
energy plus numerical residual in this closed conservative model. No intensity
or surface-flux claim from point pressure². Pressure/velocity product is local
intensity, not integrated transmitted energy without a surface integral.

Fit nearest Euclidean class means (2reference seeds) separately for each config,
band,distance,readout; freeze72 two-class templates before ANY held-out run.
Tie if |d0-d1|<=1e-12*max(d0,d1,1e-30), ambiguous incorrect. No standardization,
feature selection, phase alignment, seed replacement or reference refit.
Held-out positive4labels per decoder: require4/4 correct all3grids, no ties,
identical predictions, separation>1e-6 signed/>1e-8energy and>=5*max numerical
disagreement, feature relative error<=5%. Below absolute floor FAIL; unresolved
margin/refinement invalid INDETERMINATE; valid incorrect prediction FAIL.
Sign inversion must negate fields and preserve energy within1e-12 relative;
quadratic sign readout expected uninformative. No learning/capacity claim.

Transport threshold receiver mechanical energy>=1e-8 of supplied work;
arrival difference<=.2 normalized time and peak difference<=5% under refinement.
No zero-time source allocation called propagation. Every signal/distance kept.
Neural participation E_neural²/sum E_node² and full acoustic energy participation
(effective volume=h³*(sum e)²/sum e²) reported separately. Whole fluid+neuron
participation never adds unlike counted objects. Compare peak distant response
normalized BOTH to work and net/positive emitted energy with backflow disclosed.

S1 all standalone gates; S2 all reciprocal fixtures; S3 FLUID positive receiver
threshold and refinement allheld at6m, perband separately; S4 band differences
in launched-normalized receiver peaks >5x numerical uncertainty and >5% relative,
perdistance, not assumed monotonic; S5 all72 readout verdicts separately, primary
FLUID at6m; S6 perband/distance/readout improvement FLUID/HYBRID vs DIRECT only
if both numerically valid and either higher discrimination passing rate or
normalized receiver peak>=2x and >5x numerical discrepancy; S7 FLUID effective
neural participation>=8 and>=2x DIRECT at a common checkpoint, valid both grids,
also report fluid effective volume and signal dilution; S8 all combined balance,
refinement, zero/frozen/sign/repeat gates. No overall success score.

## Resource, records and delivery

Fluid primary4*48³ f64=3.54MB; fine28.31MB, plus work arrays/neural state, expected
<250MB active memory. Serial CPU, no GPU/parallel updates. Standalone17 runs
~0.6GB full fields; full conditional445 runs order10GB fields, <30GB output
budget, order hours CPU ceiling. Benchmark elapsed/time/disk after standalone;
do not silently shrink matrix. Refuse existing case directories; retain FAILED
and INTERRUPTED entries; no overwrite. Start with empty output roots.
Versioned QR9AC001 full field, exact dimensions/grid/time/fixture, four arrays,
FNV64 corruption check; CSV diagnostics/ledger and SHA256 manifests. Neural
schema must similarly retain actual positions/orientations/P/u/v and coupling
work, never adapt historical source-assuming records. Python independently
reconstructs coefficients, energy/geometry/features/templates/verdicts; stored
Rust flags are not evidence. Archive every source, registration, raw observation,
condition ledger and integrity receipt; test fresh viewer-free extraction.
Deliver actual-data plots with fixed physical scales, report failures, update
README/HANDOFF/index, local strict gates, historical preservation hashes, separate
commits, push/remote SHA and exact hosted CI evidence. Optional viewer deferred;
historical iGPU/default1.8 spacing unchanged, no native visual witness claimed.
