# QR11 observation schemas, version 1

Little-endian arrays; fluid x fastest. External plans/metadata carry conditions.
Owned neuron state contains no seed/source class, decoder or growing buffer.

QR11AC01:72-byte header as QR10, new magic; u64version1,N,tick,f64dt,u64fixture2,
3zero mode indices; four N^3 f64 arrays q,wx,wy,wz; trailing FNV64. Exact length
80+32N^3. Rigid positive wall slots0 and implicit lower-wall velocities0.

QR11NEU1: magic8,u64version1,node_count,tick,f64dt (40bytes),4416bytes per node,
trailing FNV64. Node order:64u8 actual palette;64f64u;64f64v;7f64packet[q,wx,wy,
wz,energy_density,power_into_node,dqdt];f64previous_pressure;u64own_age_ticks;
405f64traces;f64cumulative_loss;u64committed0/1. Tau-major(.5,2,8), each135:
7sensor,64H,64C. Every node owns its arrays, with identical implementation.

QR11OBS1: magic8,u64version1,node_count,N,f64dt,u64total_ticks (48bytes). Each
actual tick0..total: u64tick,node payloads,FNV64 for that frame. Exact length
48+(ticks+1)*(16+node_count*4416). No interpolation or external history replay.
Sampling occurs after COMPLETE physical split, including both source half kicks.
Initial packet/trace/previous0. Own age advances even with sensor disabled.

metrics.csv retains actual energies/loss, external net/positive/negative work,
source emission/backflow, exchange cancellation. kicks.csv and exchange.csv
record actual substep state/work. Python independently reconstructs every neural
ODE step and trace update, local sensors at full checkpoints and all accounting;
it is not a second complete fluid PDE integration. Packet power is current-step
work INTO that node/dt, not cumulative apparatus work. H from source internal
actuation can be nonzero with disconnected fluid; its fluid packet stays0.

plan.csv/PREREQUISITE/initial-status/events/ledger distinguish planned, started,
executed, failed and gated states. COMPLETE is never a scientific PASS.
Amplitude fixed:value/work1:CAL/same:CAL reads only unit calibration SOURCE WORK.
Calibration sensing disabled; no calibration receiver observation fits a decoder.

Morphology operations retain actual bounded before/after states, all64 scores,
accepted swaps and switch-energy receipts, plus unchanged fluid endpoint reference.
They are state continuations, not new PDE trajectories. Probe reset clears fluid,
all u/v/packets/previous/traces/age/flags/loss/work/ports. Only declared palette
persists. Source palette always externally restored at zero state. restore: prefix
on virgin reference also restores receiver at ZERO state. reset.csv records removed
energy; initial complete snapshots independently verify all zero/reset invariants.

Independent audit caches bind every case input and verifier/IO source SHA; --fresh
forces remeasurement. Integrity hashes do not establish authenticity. Every raw
field/trace, wrong/tied/invalid prediction and NOT_RUN decision stays outside Git.
