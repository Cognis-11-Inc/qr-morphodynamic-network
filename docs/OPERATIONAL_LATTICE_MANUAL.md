# Operational Lattice Manual — Experiment 0007

This manual covers only the measured heterogeneous16³ CPU/f64 bodies, eight registered seeds, fixed input energies/windows and two frozen morphology rules. It is an external laboratory interface, not an autonomous memory service. See the [full scientific report](EXPERIMENT_0007_RESULTS.md) for negative and indeterminate cases.

| Operation | Required state and exact input | Verified observable result | Energy and limits |
|---|---|---|---|
| CALIBRATE | Virgin backup P; complete reset. Pulse2183/module9 then separate reset/pulse27; E1, integrate32 each, plasticity off | Two measured signed reference responses,120 components retained externally | Each pulse injects mechanical energy1. Damping removes energy; observed drift below1%. Reference is external apparatus |
| WRITE | Externally restored virgin P and zero transients. W0=2182/module9, W1=2182/module27, E1, integrate8, single R2/R3 commit | Actual committed P and full histories, eligibility and edits; structural distinction judged separately | Commit changes stiffness/couplings and carries explicit external switching work; it is not energy-free learning. One write only |
| RESET | Any retained P; no excitation | Exact zero u,v,V,H,tick and audit accounts; P retained byte-for-byte | Clears residual mechanical activity and accounting; removed energy is an external intervention, not forgetting or passive damping |
| READ | RESET retained P. Fixed pulses2183/modules9 then27, separate resets; E1 each; integrate32, plasticity disabled | Signed u/v at2184/85/86 modules9/27 at .8/3.2/8/16/32; P unchanged | Matching amplitude depends on measured morphology stiffness by the same formula for all symbols. Label must never select pulse, sampling or amplitude policy |
| RESTORE | Explicit external virgin backup from the same seed/body | Subsequent WRITE begins at exactly the original virgin palette | RESET before/after installation. This externally replaces structure; intrinsic erasure/forgetting is not established |
| CONTROL_INSTALL | RESET plus authentic WRITE outcome, same seed/rule/virgin P | Registered ALL/port-only/REMOTE/shuffle/virgin ablations only | Experimental causal intervention; no arbitrary desired-answer palette API. Not a memory write mechanism |

## Readout capability and failure boundary

- R2 calibrated REMOTE discrimination: **PASS**; held-out 7/8, fine 7/8. A bounded operational capability only within this registered apparatus.
- R2 raw REMOTE discrimination: **FAIL**; held-out 4/8, fine 4/8. Do not describe this failed or indeterminate readout as a working capability.
- R3 calibrated REMOTE discrimination: **INDETERMINATE (numerical gate)**; held-out 4/8, fine 4/8. Do not describe this failed or indeterminate readout as a working capability.
- R3 raw REMOTE discrimination: **INDETERMINATE (numerical gate)**; held-out 3/8, fine 3/8. Do not describe this failed or indeterminate readout as a working capability.

Structural encoding is verified in 24/24 rule/seed/grid pairs, with retained P distinct after W0/W1 and unchanged by RESET.

R2 active WRITE commits change 302-392 modules across 58-69 neurons. Measured morphology switching work ranges from -0.139138668 to 0.190977160 mechanical units; negative work means external extraction at the commit. This is separate from the injected energy1 and from energy removed at RESET. All499 actual operation energy budgets are exported in operations.csv.

R3 active WRITE commits change 286-452 modules across 55-63 neurons. Measured morphology switching work ranges from -0.031521719 to 0.123632837 mechanical units; negative work means external extraction at the commit. This is separate from the injected energy1 and from energy removed at RESET. All499 actual operation energy budgets are exported in operations.csv.


The measured R2 calibrated readout passes7/8 on both grids; raw R2 fails4/8. This registered method therefore depends on its externally stored virgin reference; no general impossibility claim is made about other raw readouts. Template means are fitted externally on four training seeds and frozen; no learning occurs inside the decoder during evaluation. A positive secondary R3 result cannot replace the primary R2 verdict.

The preselected seed31/R2/W0 WRITE and two REMOTE reads reproduce 39 files byte-for-byte on the same compiler/host; cross-platform bit identity and exhaustive repeatability are not established. All writes start from virgin P; sequential storage is untested.

## Exact use and interpretation

Build `cargo build --locked --release --bin experiment_0007`. The batch CLI takes `train|evaluate|refine|repeat ROOT`; each stage must be fresh. Run train first, preserve `TRAINING_FROZEN` and the template SHA receipt, then evaluate/refine/repeat without changing features or fitting. Run the independent auditor before interpreting any scientific pass. Complete commands and dependencies are in README.

The Rust `Operator` exposes immutable physical inspection, `write`, `advance`, `commit`, `reset`, `read`, `restore`, `control`, and operation-aware checkpoints. WRITE must end at8 for commit; READ ends at32. Idle stepping, premature/duplicate commit, writes to retained edited structure, calibration of edited structure, invalid module/grid/rule and foreign control outcomes are rejected. `read` receives no write label.

Do not infer distributed associative recall, intelligence, resilience, generalization, capacity, interference tolerance, useful sequential writes or Principle 002 from these operations. Frozen/no-write/virgin controls, signed fields, actual energy matching and registered numerical gates remain mandatory. The viewer is unnecessary for reproduction or review.
