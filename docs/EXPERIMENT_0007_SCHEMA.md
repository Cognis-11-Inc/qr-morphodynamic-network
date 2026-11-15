# QR7 observation and operation schema 1

`QR7FLD01` is a 40-byte outer header: magic (8 bytes), little-endian
u64 schema=1, physical impulse port, operation (0 CALIBRATE, 1 WRITE,
2 READ), adaptation rule (0 calibration, 2 R2, 3 R3). It is followed by an
unchanged QR6 signed field body and an outer FNV-1a u64 checksum over all
preceding bytes. The inner body has its own checksum. Reusing the QR6 field
codec does not use its historical viewer/source presentation conversion.
QR7 port metadata is authoritative. WRITE uses 2182; CALIBRATE/READ use 2183.

The inner body begins `QR6FLD01`, then seven little-endian u64 words:
schema=1, tick, dt IEEE-754 bits, seed, configuration=2, label byte length,
module (9 or 27); label bytes follow, then 262144 palette bytes (neuron,
module row-major), 262144 signed f64 displacements, 262144 signed f64
velocities, and FNV-1a checksum. The constant body label `QR7` is not an
encoded symbol or decoder feature. Full condition identity is external in
the ledger and directory names. These names are never numeric decoder inputs.

`features.f64` in each READ pulse stores 60 little-endian f64 numbers;
`<protocol>.f64` stores the two pulses concatenated (120 numbers). Order is
pulse [9,27], time [.8,3.2,8,16,32], site [2184,2185,2186], observed module
[9,27], field [u,v]. No header/metadata/labels are present. `outputs.f64`
stores 12 signed output values in site/module/field order every tick from
zero. Tick/time are implicit in `parameters.csv` and row number.

WRITE `early.q7p` begins `QR7PRB01`, then for every tick: u64 tick,
6 sites [0,2182,2183,2184,2186,2191] × 64 modules × (u,v) f64. These are
engine measurements, not fixtures. Full V/H/S arrays have one f64 per
neuron/module. `edits.csv`, `switch.csv` and `commit.csv` expose each actual
edit, per-neuron energy partition, and total external actuation work.
WRITE commits only at physical time 8; its `post.q7f` shares that tick.

`RESET` receipts certify exact zero transients/histories/audits and retained
P. `REUSED` contains an actual virgin calibration pulse directory name;
`EQUIVALENT` records equality of the complete initial-state fingerprint,
including P,u,v,V,H,dt,tick and all energy accounts. Reused observations retain
the original CALIBRATE operation. They are not independent measurements.

`ledger.csv` lists logical protocols, physical trajectories, and reference
reuse. `TRAINING_FROZEN` binds numeric template files to FNV checksums before
evaluation is allowed. Final packages also bind sources and evidence with
SHA-256; neither checksum is an authenticity signature. `predictions.csv`
contains external labels after numeric-only prediction. Nearest means use
only REMOTE_ONLY training seeds 7,19,31,43. Held-out and finer-grid cases
cannot enter training. Raw and calibrated models and R2/R3 stay separate.
