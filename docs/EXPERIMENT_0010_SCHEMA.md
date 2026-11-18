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
