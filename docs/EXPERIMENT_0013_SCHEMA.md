# QR13 external scientific observations and split schema

The original QR12 ABI remains authoritative: signed64 u/v, palette64, packet7,
trace405 and local controller per node, one shared fluid, signed work/port ledgers,
and sparse complete-field checkpoints. No physical file format is changed.

`inventory.json` has one row per original82 executions with actual metadata,
source directory, stream/audit/dataset SHA256, original archive SHA256, causal
checkpoint ancestry, seed family, partition, physical/numerical/protocol validity,
duplicate marker, diagnostic marker and model eligibility. All invalid controls
remain inventoried. The prior physical audit receipt is bound to every raw-file
SHA; it is evidence distinct from extraction verification. `splits.json` records
complete seed-family partitions; descendants/refinements/repeats never move.

`data/STAGE__CASE.npz` stores actual .2-time-unit subsamples: absolute time, raw
ticks, u/v(T,N,64), packet(T,N,7), z(T,N,405), palette(T,N,64), controller(T,N,4),
independently reconstructed energy(T,N), global_metrics(T,9). Controller order:
latch,events,attempts,time-since-last-success (seconds; initial last=0). Global
order:fluid,neural,loss,force_work,switch_work,positive,negative,port_net,cancellation.
QR11 oracle controller is explicitly unavailable/zero and oracle never modeled.
Displacement/velocity/energy/pressure use the engine's normalized physical units;
these are not calibrated biological/QR-material measurements. No interpolation
of sparse fields into dense truth. Full fields remain in original archives.

Forecast origins use the three observed times t-.4,t-.2,t. Labels are direct
states t+.2,t+1,t+2; all inputs are at or before t. Target blocks are64 u,64 v,
pressure,energy. Local inputs use own128 mechanical entries,packet7,energy,
18 trace entries [0..5,135..140,270..275],4controllers and own clock. Global
concatenates four such bodies, current/past global9 and a four-entry current
apparatus forcing-kind indicator. Explicit morphology adds current one-hot
palette64x5 per observed node. State-only still observes physical energy and
history, which can contain indirect structural information; its ablation tests
incremental explicit palette information, not total removal of all structure.

`crossing` is an evaluation-only flag for an interval crossing16/24/32, including
vetoed opportunities; `accepted` separately marks actual count changes. Neither
is supplied as a future feature. Local models never receive global values.
Normalization/target RMS/PCA fit TRAIN401 only; scale floor1e-8 targets and1e-6
input standard deviations. No test-fit normalizers. Historical419/427 tests are
retrospective, not fresh discoveries. Reserved431/433/439/443/449/457/461/463 are
prospective final families; grids/policies/windows are paired, not extra samples.

`models/*normalization.npz`, baseline coefficients, PyTorch weights and JSON
records bind source/dataset/checkpoint hashes. Full per-window/horizon/node/raw
predictions retain wrong forecasts and invalid-case diagnostics. `selection.json`
is immutable before final physical execution; `freeze.json` seals it together
with all learned/baseline/latent files and candidate registry. No refit on tests.

The CPU learner is optional for historical physics. Install `requirements-learn.txt`
for training or the dedicated hosted CPU smoke tests. Original Python quality jobs
can run extraction/alignment tests without torch. No GPU/CUDA execution is required.
