# QR Neural Memory System

An experimental, Rust-first investigation of a mutable, QR-inspired computational matrix.

We investigate what the substrate's rules actually permit. Useful memory behavior and any unexpected computation must be measured, reproduced, and explained before they become claims.

Follow the [experiment progression index](docs/EXPERIMENTS.md) for separate designs, measured outcomes, and deferred questions. Experiments 0001/0002 remain frozen. Experiment 0003 adds a deterministic 16³ lattice and a separate Bevy scientific observatory.

## Initial direction

- **4,096 independently reconfigurable QR neurons**. Experiment 0001 uses a **64 × 64 network**, each neuron containing its own **8 × 8 spatial array of colored modules**. These are explicit experiment parameters; the population count alone does not define geometry.
- Approximately **80% Rust / 20% Python**, a flexible architectural target. Rust owns the engine and deterministic experiments; Python supports analysis, statistics, plots, and comparisons.
- CPU execution and deterministic experiments first.
- Distributed representations, local interactions, and experimentally defined plasticity.
- No conventional QR error correction or conventional neural-network architecture imposed at the start.
- Persistence and deterministic replay as research requirements for the engine.

Experiment 0001 implements five module values (empty, red, green, blue, yellow). Their spatial arrangement is the neuron's shape. Color and shape affect computation. Ripple amplitudes and momentum are transient and separate from persistent module configuration. Compatibility with standard QR codes is not an initial objective.

## QR Neural Memory Principle 001

A learned association is represented by persistent, experience-dependent changes distributed across the internal states of many QR neurons. No individual QR neuron is assigned ownership of the complete association. Retrieval must arise from interactions among these local states under explicitly defined deterministic rules.

See [PRINCIPLES.md](PRINCIPLES.md) for the design consequences.

**Morphic QR Neuron Principle 002 is proposed:** intrinsic response and neighbor
exchange govern excitation, internal morphology governs reception/retention/
transmission, and sustained interactions may change morphology under an explicit
plasticity law. The [full proposed wording and experimental consequences](PRINCIPLES.md#morphic-qr-neuron-principle-002--proposed)
keep transient excitation distinct from persistent memory. Existing frozen-medium
experiments do not implement that proposed plasticity mechanism.

## Hypothesis R1: distributed resilience

Associations encoded through overlapping, persistent changes across multiple QR neurons can remain retrievable after partial loss or corruption of the substrate.

**Untested.** We will attack this hypothesis by verifying A → B retrieval, then progressively disabling neurons under matched random and contiguous regional damage. Graceful degradation is a target to test. Capacity, redundancy, and interference must be measured together. Experiment 0001 implements eight-neighbor connectivity without demonstrating working association retrieval; lesion testing is deferred.

See [HYPOTHESES.md](HYPOTHESES.md) and the proposed [R1 experiment protocol](EXPERIMENT_R1.md). Damage illustrations are not measured retrieval results.

## Experiment 001: first measurable memory behavior

1. Teach the substrate associations using an explicit, documented update rule.
2. Attempt reconstruction from incomplete cues.
3. Measure whether learning new associations damages older ones.
4. Compare results against controls and record the initial state, parameters, input sequence, and results needed to reproduce them.

A further research question is whether retrieving a memory can change the substrate and alter subsequent propagation. This remains a hypothesis to test, as does computation beyond associative retrieval.

## Status

Experiment 0001 is implemented and measured: a local color-transition baseline and a two-scale damped-wave candidate, with persistent per-neuron module arrays, synchronous updates, transient reset, partial-cue recall, sequential training, controls, ablations, and exported snapshots. **None of the 24 registered trials met the association or retention criteria.** The ripple arm produced empty outputs and no persistent changes at the registered distance/duration; the local baseline changed 16 neurons but reconstructed targets poorly. No successful learning, distributed-memory mechanism, or resilience is demonstrated.

Read the [rules and preregistered criteria](EXPERIMENT_0001.md) and [actual results and failures](docs/EXPERIMENT_0001_RESULTS.md). Raw evidence remains local under the ignored `results/` directory.

To reproduce, use a fresh output directory for each run:

```sh
cargo run --locked --release --bin experiment_0001 -- results/my-experiment-0001
.venv/bin/python -m analysis.experiment_0001 results/my-experiment-0001
```

The runner refuses an existing output directory. The analyzer independently checks raw outputs, metrics, snapshots, change locations/counts, and trial decisions. A completed execution is distinct from a positive scientific result.

Read [AGENTS.md](AGENTS.md) and [HANDOFF.md](HANDOFF.md) when resuming work.

## Experiment 0002: intrinsic dynamics, transport, and resonance

Stages T and R are implemented in a separate runner and measured across **1,101 cases per run**, with two byte-identical complete runs. Each full network still contains 4,096 independent 8 × 8 color-and-shape configurations. Displacement and velocity are transient; plasticity is disabled.

- **T: negative at the registered four-hop usability threshold.** All 96 required probes detected signals, but their normalized transfer was too weak. Nearer-distance transmission is documented separately.
- **R: indeterminate.** 28/36 isolated-neuron sweeps met the spectral-peak criterion; 11/12 shape pairs exceeded the sensitivity threshold. Four timestep-convergence checks failed, and the full positive criterion was not met.
- **P: not run.** No persistent reconfiguration, memory learning, or resilience is claimed.

See the [frozen registration](EXPERIMENT_0002.md) and [measured results, controls, and figures](docs/EXPERIMENT_0002_RESULTS.md). Scalar, isolated-neuron, nine-neuron diagnostic patches, and limited full-network spectral cases are explicitly distinguished.

```sh
cargo run --locked --release --bin experiment_0002 -- results/my-experiment-0002
.venv/bin/python -m analysis.experiment_0002 results/my-experiment-0002
```

Raw evidence stays under ignored `results/` folders. Numerical verification uses the Python standard library; optional figures use `requirements-plot.txt`.

## Experiment 0003: volumetric lattice and scientific observatory

Implemented and measured: **4,096 independently configured neurons in 16 × 16 × 16**,
Cubic6 and Cubic26 policies, plus a Grid2D8 regression adapter. Each neuron still
owns its actual 8 × 8 color-and-shape configuration. Two complete 111-case suites
produced byte-identical evidence. Topology and configuration affect propagation;
no learning, resonance or resilience success is claimed.

The separate Bevy viewer displays measured live or recorded state, with camera
controls, neuron selection, an actual internal-module panel, slicing and bounded
replay. Default graphics preference is low power, verified on the AMD Raphael
iGPU, leaving the 5060 Ti available for models. The scientific engine remains CPU-only.

```sh
cargo run --locked --release --bin experiment_0003 -- results/my-experiment-0003
.venv/bin/python -m analysis.experiment_0003 results/my-experiment-0003
CARGO_BUILD_JOBS=1 cargo run --locked --manifest-path viewer/Cargo.toml -- --recording results/my-experiment-0003/case-0000
```

The viewer starts paused in REPLAY. Space plays, Period steps, right-drag orbits,
and typing an ID then Enter selects a neuron. Add `--live` for the same seeded CPU
fixture. Camera and filters never modify the scientific substrate.

Read the [frozen design](EXPERIMENT_0003.md),
[measured results and native captures](docs/EXPERIMENT_0003_RESULTS.md), and
[viewer operator guide and isolated checks](viewer/README.md). Large recordings
remain local and ignored; generate them into a fresh folder after cloning.

## Experiment 0004: extended propagation and dual-wave interference

Implemented and measured: two identical 35-execution suites, 1,024 steps at
dt0.1 plus matched-time half-step controls. A-only, B-only, same-polarity and
opposite-polarity dual-source fields were integrated independently through the
frozen Cubic6 medium. Full signed-state superposition residuals stayed below
1.45e-15. **All eight long-window half-step comparisons failed the 10% screen**
(27.8–30.4% worst relative error). Visible interference does not establish a
converged trajectory, a persistent change or memory.

```sh
cargo run --locked --release --bin experiment_0004 -- results/my-experiment-0004
.venv/bin/python -m analysis.experiment_0004 results/my-experiment-0004
CARGO_BUILD_JOBS=1 cargo run --locked --manifest-path viewer/Cargo.toml -- --experiment-0004 --recording results/my-experiment-0004/group-01/2 --select 2184 --slice-z 8 --play --replay-hz 0.5
```

Read the [frozen registration](EXPERIMENT_0004.md),
[measured results and signed-field figures](docs/EXPERIMENT_0004_RESULTS.md),
and [replay controls](viewer/README.md). Experiment 0004 playback is explicitly
replay-only, with both source IDs and the arm labeled. Persistent changes from
interacting disturbances remain a later experiment.

## Every-tick 3,072-tick extension and portable agent report

The current homogeneous AB+ case now has a separately registered **3,072-tick**
run, with all **3,073 integer observations** saved. Two runs and native replay
agree exactly. Both global maxima remain below1e-6 from tick2579 through3072;
final displacement/velocity peaks are8.14e-8/1.18e-7, nonzero. This measured decay
is subject to the original failed long-window timestep screen.

```sh
cargo run --locked --release --bin experiment_0004_decay -- results/my-decay
.venv/bin/python -m analysis.decay_0004 results/my-decay
CARGO_BUILD_JOBS=1 cargo run --locked --manifest-path viewer/Cargo.toml -- --decay-0004 --recording results/my-decay --select 2184
```

The stream reads one frame at a time; full cube is the default. Space plays,
Period steps exactly one tick. Rendering stalls slow playback rather than skip
recorded ticks. Inspect the global displacement/velocity readout alongside color.

The analyzer creates `agent-report/REPORT.md` and `AGENT_REPORT.zip`: clear setup,
rules, every-tick global data,32neuron traces,4,096spatial summaries and integrity
hashes. Another agent can analyze these without a viewer/video or the large binary
stream. Read the [extension registration](EXPERIMENT_0004_EXTENSION.md) and
[measured report](docs/EXPERIMENT_0004_EXTENSION_RESULTS.md).

## Research foundations

The [foundational research reading list](docs/FOUNDATIONAL_PAPERS.md) collects the prior work we will build upon when designing neuron state, local learning rules, and experimental comparisons. It is a research foundation, not evidence that our substrate works. Paper-specific mechanisms and assumptions must be distinguished from our own hypotheses and measured results.

## Development checks

Rust is pinned in `rust-toolchain.toml`. Python requires 3.12 or newer; hosted CI checks 3.12 and 3.14. Create an isolated Python environment and install the pinned development tools:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

Run the same checks used by severe CI:

```sh
cargo fmt --all -- --check
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo test --locked --all-targets --all-features
cargo test --locked --doc --all-features
cargo build --locked --release --all-targets --all-features
RUSTDOCFLAGS='-D warnings' cargo doc --locked --no-deps --all-features
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -W error -m unittest discover -s analysis -t . -v
.venv/bin/python -W error -m compileall -q analysis
```

CI additionally sets `RUSTFLAGS='-D warnings'`. Workflow: [Severe CI](https://github.com/Cognis-11-Inc/qr-neural-memory-system/actions/workflows/ci.yml).

The isolated viewer additionally has a headless compilation/test CI job; it does
not open a window or establish native rendering correctness on GitHub runners.

## Experiment 0005: morphic response and energy audit

[Registration](EXPERIMENT_0005.md) freezes a new second-order split integrator,
actual mechanical energy accounting, paired spatial palettes and bounded local
plasticity/re-exposure. Prior experiments stay unchanged. Install the independent
analyzer with `.venv/bin/python -m pip install -r requirements-analysis.txt`.

```sh
cargo run --locked --release --bin experiment_0005 -- results/my-0005 numerical
.venv/bin/python -m analysis.experiment_0005 results/my-0005 --stage numerical
cargo run --locked --release --bin experiment_0005 -- results/my-0005 a
# B requires the long-window gate; C requires the time-32 gate.
cargo run --locked --release --bin experiment_0005 -- results/my-0005 c
.venv/bin/python -m analysis.experiment_0005 results/my-0005
CARGO_BUILD_JOBS=1 cargo run --locked --manifest-path viewer/Cargo.toml -- --experiment-0005 --recording results/my-0005/a-heterogeneous-7-AB+ --node-spacing 1.8 --select 2184
```

Each stage requires a fresh ledger; completed case folders are never overwritten.
A separate `repeat` stage in a fresh root repeats heterogeneous 7 AB+ for exact
comparison. `b` is intentionally rejected if the long-window numerical gate fails.
See [record schema](docs/EXPERIMENT_0005_SCHEMA.md) and the results report for
execution coverage. Scientific gate failure is separate from software test success.

[Experiment 0005 measured results](docs/EXPERIMENT_0005_RESULTS.md): short-window
persistent response passes; long-window accuracy fails and M5-B remains gated.
The same 63 local edits survive transient reset at both registered grids. This
is not associative memory. Portable data live under ignored `results/experiment_0005`.

## Experiment 0006: multi-module morphology and causal ablations

The [frozen registration](EXPERIMENT_0006.md) separates refined numerical gates,
forcing-coordinate diagnosis, single/recolor/shape-swap rules and source/off-source
causal re-exposure. Prior scientific files remain unchanged. Use a fresh root:

```sh
cargo run --locked --release --bin experiment_0006 -- results/my-0006 n
.venv/bin/python -m analysis.experiment_0006 results/my-0006 --stage n
cargo run --locked --release --bin experiment_0006 -- results/my-0006 d
cargo run --locked --release --bin experiment_0006 -- results/my-0006 m
cargo run --locked --release --bin experiment_0006 -- results/my-0006 c
.venv/bin/python -m analysis.experiment_0006 results/my-0006
cargo run --locked --release --bin experiment_0006 -- results/my-0006-repeat repeat
```

D/M/C require the independently evaluated numerical short gate. A failed long
gate forbids long-time interpretation. `repeat` uses seed19/module9/E1/R3 and
retains the exact original condition ID. No stage overwrites existing evidence.
See [QR6 schema](docs/EXPERIMENT_0006_SCHEMA.md) for actual signed checkpoints,
probe histories, local eligibility and palette arrays. The isolated viewer's
`--experiment-0006` mode shows recorded before/after morphology at spacing1.8.


[Experiment 0006 results](docs/EXPERIMENT_0006_RESULTS.md): refined numerical
screen passes; both multi-module rules and selected post-reset off-source causal
gates pass. No associative memory or useful-recall claim. All190 logical cases
are accounted for as168 executions plus22 explicit reuses, with a separate repeat.

```sh
.venv/bin/python -m analysis.summarize_0006 results/my-0006
.venv/bin/python -m analysis.plot_experiment_0006 results/my-0006 docs/figures
.venv/bin/python -m analysis.report_experiment_0006 results/my-0006 docs/EXPERIMENT_0006_RESULTS.md
.venv/bin/python -m analysis.package_experiment_0006 results/my-0006 --native results/0006-native --repeat results/my-0006-repeat
```

## Experiment 0007: bounded operations and held-out readout

The [frozen registration](EXPERIMENT_0007.md) fixes CALIBRATE/WRITE/RESET/READ/
RESTORE, two write modules, a label-independent two-pulse read, eight causal
controls, numeric-only nearest-template decoding, and all held-out fine cases.
QR6 physics and earlier scientific files remain unchanged. The external virgin
reference and training templates are apparatus, not lattice memory. See the
[QR7 schema](docs/EXPERIMENT_0007_SCHEMA.md).

Execute serially in a **new** root; each stage refuses to overwrite its folder:

```sh
cargo build --locked --release --bin experiment_0007
.venv/bin/python -m analysis.package_experiment_0007 results/my-0007 --record-provenance target/release/experiment_0007
target/release/experiment_0007 train results/my-0007
sha256sum results/my-0007/train/template*.f64 > results/my-0007/TRAINING_SHA256.txt
target/release/experiment_0007 evaluate results/my-0007
target/release/experiment_0007 refine results/my-0007
target/release/experiment_0007 repeat results/my-0007
.venv/bin/python -m analysis.audit_experiment_0007 results/my-0007
.venv/bin/python -m analysis.protocol_experiment_0007 results/my-0007
.venv/bin/python -m analysis.review_experiment_0007 results/my-0007
.venv/bin/python -m pip install -r requirements-plots.txt
.venv/bin/python -m analysis.report_experiment_0007 results/my-0007
```

The auditor may follow the serial engine with `--follow` in another terminal;
it performs analysis only, never parallel physics updates. Caches bind verifier
source and every input SHA; move `ROOT/audit` aside to force fresh recomputation.
The small `review` command independently reconstructs classification and feature
margins using numeric observations; it does not recheck full-field energy/rules.
A failed scientific readout is a completed experiment, not a reason to retune.
Full package creation additionally expects `EXECUTION_PROVENANCE.json` recording
the actual executable/compiler/source identities:

```sh
.venv/bin/python -m analysis.package_experiment_0007 results/my-0007 --downloads /home/cognis/Downloads
```

The complete matrix has688 logical trajectories:496 actual plus192 explicit
calibration reuses, with3 separate repeat executions. Estimated serial CPU time
is60–80 minutes and signed-field storage roughly12GB. Viewer-free review/data
and full-field companion archives carry member SHA manifests. Scientific results
and the measured Operational Lattice Manual are generated only after the full
independent verification completes.

[Measured Experiment 0007 results](docs/EXPERIMENT_0007_RESULTS.md): R2 calibrated
REMOTE readout passes7/8 on both registered grids; raw R2 fails4/8. R3 remains
operationally indeterminate after a3.799% full-field refinement failure against
1.5%, despite stable reduced features. Structural encoding and the selected
repeat pass. This is calibration-dependent discrimination, not associative recall.
The [Operational Lattice Manual](docs/OPERATIONAL_LATTICE_MANUAL.md) records exact
operations, measured energy costs, reproducibility and failed capabilities.

## Experiment 0008: frozen energy distribution and communication

[Registration](EXPERIMENT_0008.md) freezes97 actual executions, four equal-energy
single inputs, two dual polarities, ZERO and the independent B superposition
basis. All palettes stay frozen. [QR8 schema](docs/EXPERIMENT_0008_SCHEMA.md)
records full signed fields and per-module mechanical partitions. Distal readouts
use fixed six-sensor regions with matched energy/signed budgets; no near/far
pooling, palette encoding or internal training. Energy arrival and discrimination
have separate verdicts. Use a fresh root and the same compiled executable:

```sh
cargo build --locked --release --bin experiment_0008
mkdir -p results/my-0008
cp target/release/experiment_0008 results/my-0008/registered-runner
.venv/bin/python -m analysis.package_experiment_0008 results/my-0008 --record-provenance results/my-0008/registered-runner
results/my-0008/registered-runner train results/my-0008
# In a second terminal; performs independent analysis, never physics updates:
.venv/bin/python -m analysis.audit_experiment_0008 results/my-0008 --follow
# In the first terminal, after train returns; fit awaits independent TRAIN_READY:
.venv/bin/python -m analysis.experiment_0008 results/my-0008 fit
results/my-0008/registered-runner evaluate results/my-0008
results/my-0008/registered-runner refine results/my-0008
results/my-0008/registered-runner repeat results/my-0008
# Wait for the auditor's verification.json, then:
.venv/bin/python -m analysis.experiment_0008 results/my-0008 review
.venv/bin/python -m analysis.report_experiment_0008 results/my-0008
.venv/bin/python -m analysis.package_experiment_0008 results/my-0008 --downloads /home/cognis/Downloads
```

Record executable SHA, compiler, source commit and template-freeze timing before
interpretation; this delivery's provenance is in its ignored execution receipt.
Estimated physics time20–35 minutes, plus verification/archives; no GPU or viewer
is needed. The 404 external class-mean readouts are fixed before held-out data.
G/T/SH/KP are quadratic energetic observables; U/UV retain signs. Whole-field
refinement, absolute detectability, numerical separation and classifier gates
are independent. Never interpret energy reaching a shell as proof that its
input remains distinguishable there. `--fresh` forces full independent auditing.
Portable source includes all embedded specifications, geometry JSON and fixtures.

[Experiment 0008 measured results](docs/EXPERIMENT_0008_RESULTS.md): equal-energy
module9/27 inputs are distinguishable from spatial energy at4 hops (8/8 held-out
on both grids), including channels outside9/27. Global energy reaches6/8; spatial
energy at6 hops fails. Energy is invariant under complete sign inversion, while
signed UV resolves sign at2/4 hops. Registered broad-participation and dual-energy
discrimination gates fail. P1/P4/P6 pass; no overall success score or memory claim.
All97 cases,582 signed/energy checkpoints,404 readout models and9696 predictions
are retained with complete negative/ambiguous and numerical evidence.
