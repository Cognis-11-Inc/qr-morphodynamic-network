# QR8 measured records, schema 1

Full checkpoints use QR8FLD01. Header72 bytes: magic8, then little-endian
schema1(u64), signal code(u64), portA2182(u64), portB2186(u64), actual initial
amplitudeA(f64), amplitudeB(f64), inner-body length(u64), field count262144(u64).
Signal codes0..7: S9p,S27p,S9m,S27m,ABp,ABm,ZERO,B27p. ZERO has no active input;
unused ports have amplitude0. All code/module/amplitude identities are audited.

The inner body is unchanged QR6FLD01: magic, seven64-bit words schema1,tick,
dtbits,seed,configuration0,label byte length,module, then actual condition ID
`s<seed>_<signal>`, all262144 P bytes (neuron,8x8 module row-major), full signed
u then v arrays (262144 little-endian f64 each), inner FNV-1a64 checksum. QR8 then
appends full per-module kinetic K and onsite/half-edge Q arrays, same dimensions
and indexing, and an outer FNV checksum. Complete bytes, not interpolation or
activity surrogates. Physical time<=32, dt.025/.0125, module9/27.

QR8REG01 region stream: magic8, u64 schema1, u64 regions10, u64 scalars12.
Each tick: u64tick, then10x12 little-endian f64. Region orderA1,A2,A3,A4,A6,
F1,F2,F3,F4,F6. Scalars: full geometric mechanical energy, receiver mechanical
energy, receiver/retained fraction, receiver motion energy, outside-injected
mechanical energy, outside-injected motion energy, outside9/27 mechanical energy,
outside9/27 motion energy, minimum receiver-neuron energy, maximum, mean,
population standard deviation. Full A4 includes B's energy; receivers never
include either source. F-region full and receiver sets are the same.

QR8PRB01: magic8, u64schema1,u64probe count50,u64module count4, then50u64 IDs and
4u64 modules[9,27,10,18]. Each tick: u64tick and50x10f64. Each neuron records
mechanical energy,motion energy,u9,v9,u27,v27,u10,v10,u18,v18. All samples are
actual engine ticks. IDs are the fixed region-probe union plusA,B,2184,0,4095.
Root regions.json copies the frozen registration; Python derives and checks it.

Global metrics.csv holds every actual tick's mechanical components, exact damping
losses, zero forcing/switch work, relative drift, absolute field maxima, participation, active receiver count,
and full-population outside-injected/outside9/27 mechanical/motion energies.
Motion means K+onsite, excluding half-edge allocation. K/Q and signed fields are
retained at0,.8,3.2,8,16,32; only5 nonzero times enter discrimination features.

Derived numeric feature files are little-endian f64 ONLY; no labels/metadata.
G is the5 total-energy scalars. Each A/Fregion/mask produces SH (5 region sums),
T(total per-module energy), U(displacement), KP(kinetic,potential), UV(displacement,
velocity), in time/sorted selected-probe ID/module/component order. The all mask
uses64 modules; cross excludes9/27, leaving62. Six probes everywhere: T/U1920 or
1860; KP/UV3840 or3720. Source names, expected classes, seed IDs and palette bytes
remain external. T/U and KP/UV have equal scalar observation budgets respectively.

models/*.f64 store two external class means, class0 then1, dimension declared
in freeze.json, SHA bound. train/TRAINING_FROZEN binds freeze.json before evaluation
starts. No new model is fitted after training. Global G versus region SH share
5 scalar samples but cover different spatial extents, disclosed in results.

Checksums are corruption checks; source/data SHA manifests are integrity evidence,
not signatures. Ledger status identifies complete, failed or not-run cases. A
preselected repeat uses the same physical ID in a separate execution directory;
no reuse is counted as a new measurement. Scientific failure is not software failure.
