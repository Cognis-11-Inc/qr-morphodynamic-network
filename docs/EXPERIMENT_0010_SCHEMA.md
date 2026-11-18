# QR10 observation schema version 1

`QR10AC01` full signed fluid checkpoints: 8-byte magic, then little-endian
u64 version=1,N,tick; f64 dt; u64 fixture kind (0 mode,1 Gaussian,2 zero),
three u64 mode indices. Header72 bytes. Four N³ f64 arrays q,wx,wy,wz,
x fastest, cell pressure and positive-face normal velocities. Final u64 FNV64
of all preceding bytes. Exact length80+32N³. Rigid outer velocity slots zero.
Checksum is corruption detection, not authentication. SHA256 manifests bind files.

Each case has metrics.csv with every tick/time, compensated actual energy,
max absolute q/w and modal projections; probes.csv has21 nearest-cell samples
per tick: three axes, offsets-6,-4,-2,0,2,4,6 from(12,12,12).
Pressure and averaged adjacent face velocities plus half-face-shared energy
density are retained. These are observations, not every-tick full fields.
Full fields at registered quarter/half/final horizons, including tick0.

plan.csv records initial NOT_RUN state; events.csv records STARTED/COMPLETE;
ledger.csv records completed grid/dt/row count/wall time. Case directories refuse
overwrite. Absence from completed ledger does not mean scientific failure.
COMPLETE means execution finished, never a scientific verdict.

Independent verification.json keeps categories A..E and Level A/B separately.
gates.csv preserves every individual measured gate; observations.csv retains
fsum and reporting errors, naive accumulation discrepancy, combined/component
errors, exact split residual, temporal and corrected spatial error, phase,
amplitude and speed. rates.csv records each measured ratio/order or explicitly
INDETERMINATE. summary.csv includes actual all-tick energy drift per case.
Corrected spatial fields exist only in the analysis calculation; raw fields are
never altered. Their temporal correction is derived from the exact split mode,
not fitted to observations. Long240 is an energy/reliability test only.

The ignored execution provenance binds source HEAD, every tracked source hash,
compiler and original executable before measurement. Packaged delivery source
can have a later HEAD and is identified separately. Historical protected hashes
exclude only the four explicitly shared integration/documentation files.

## Stationary coupling records

The pilot reuses QR10AC01 with kind2 meaning zero initial fluid; nonzero later
fields are valid coupled observations. Each checkpoint also has
`TICK.neuron.csv`: exact neuron/module ordering, palette0..4, signed u/v for
2x64 modules, schema1 identified by metadata.csv (seed, band index0..2,
module9/27, separation, grid/dt, control and actual stationary coordinates).
Independent repeated executions retain identical physical metadata.

`history.csv` contains receiver-only full64 u/v at every.1 time. `probes.csv`
contains actual local fluid pressure, co-timed face-averaged velocity and energy
density at that receiver. `metrics.csv` has all-tick separate fluid, source,
receiver and optional direct-spring energies, damping, signed and positive source
work, transducer work/backflow and accumulated exchange cancellation.

`kicks.csv` records BOTH source half-kicks every tick: before/after actual neural
velocity and applied impulse, permitting independent forcing/work reconstruction.
`exchange.csv` records every forward/reverse transducer substep, neuron/module,
normalized pressure projection x before/after, neural velocity before/after and
actual support fluid/neural energy deltas. `ports.csv` keeps signed net, positive,
backflow and neural work per port. Fluid projection x=h^(3/2) sum(W q)/norm(W),
so delta fluid energy=.5 delta(x²), delta neural kinetic=.5 delta(v²), within
roundoff. Full support energy deltas are observed independently in Rust.

Cumulative source-positive and receiver-positive fields count work INTO fluid;
a negative receiver net means fluid supplied net energy to that neuron. These
are exchange work, not external work. Exact kick work is external; initial
states are zero. All palettes stay frozen. Neuron energy includes intrinsic and
internal-cardinal spring terms; DIRECT also includes its explicitly artificial
inter-neuron spring. No external historical Cubic6 edges exist in FLUID.

The width1.5m tensor hats overlap at2m separation. A causal receiver response
therefore does not alone prove delay across disjoint supports or long-range
transport. The conditional4/6m cases have disjoint supports. This geometric
limitation must remain attached to any2m pilot observation.

## Extended matrix and frozen readout

Metadata schema2 marks three-neuron interference observations; the separate
third_neuron.csv gives its generator identity and coordinates. Two-neuron
extended cases retain schema1, with kicks.csv adding explicit driven-neuron ID.
Readers accept the pilot's implicit source0 and extended explicit ID. Interference
source_energy/source exchange aggregate emitters0/2; receiver1 remains separate.
Every actual neuron still has64 independently recorded palette/u/v modules.

Extended train/evaluate/interference directories each have exact plans, events
and completion ledgers. reuses.csv maps the two original pilot calibration cases
without synthesizing new executions. templates.json freezes9 numeric decoders,
18 class vectors of12928 scalars and calibration input SHA256 before held-out
execution. TEMPLATES_SHA256.txt binds the untouched frozen file. Decoder fitting
source is identified in that file and preserved in source-freezes/194afd7.tar.gz;
later C5 reporting additions do not refit means or change predictions.

predictions.csv retains all72 grid-specific held-out predictions, both class
distances and ties/errors. decoders.csv and uncertainty.csv keep each independent
band/distance gate and separation/grid-error budget. responses.csv records
work, positive emission/backflow, receiver peak per work/per positive emission,
arrival and peak time for every held-out case. signed_spectra.csv preserves real
and imaginary DFT pressure coefficients with actual normalized frequencies.
band_comparisons.csv applies the registered5x measured uncertainty criterion,
requiring standalone Level B and coupled numerical validity. interference.csv
contains all signed superposition residuals and signed fluid-energy cross terms.
These are measured deterministic finite-case results, not statistical population
accuracy, physical seawater attenuation or associative memory.
