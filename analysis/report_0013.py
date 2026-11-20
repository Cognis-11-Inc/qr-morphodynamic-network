"""Measured QR13 figures and separate results/exploitation reports, never synthetic data."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis.dataset_0013 import save
from analysis.experiment_0009 import rows


def report(root, output):
    root = Path(root)
    output = Path(output)

    def load(name):
        return json.loads((root / name).read_text())

    forecast = load("forecast-verdicts.json")
    latent = load("latent-verdicts.json")
    selection = load("selection.json")
    physical = load("physical-execution.json")
    forecast["G4"] = latent["G4"]
    save(root / "scientific-verdicts.json", forecast)
    train = load("training.json")
    lm = load("latent-models.json")
    baseline = load("baselines.json")
    inv = load("inventory.json")
    prospective = load("prospective-inventory.json")
    metric = rows(root / "prospective_test-metrics.csv")
    latentrows = rows(root / "prospective_test-latent.csv")
    figures = output / "figures"
    figures.mkdir(exist_ok=True, parents=True)

    def finish(name):
        plt.tight_layout()
        plt.savefig(figures / f"experiment_0013_{name}.png", dpi=150)
        plt.close()

    plt.figure(figsize=(9, 4))
    labels = ["TRAIN401", "VALID409", "RETRO419/427", "FINAL8 seeds"]
    counts = [
        sum(r["partition"] == p for r in inv + prospective)
        for p in ("train", "validation", "retrospective_test", "prospective_test")
    ]
    plt.bar(labels, counts)
    plt.ylabel("Actual trajectories (dependent within seed)")
    plt.title("Scientific partitions:4 historical +8 new seed families")
    finish("partitions")
    primary = next(r for r in train if r["id"] == selection["primary"])
    plt.figure(figsize=(10, 4))
    records = [r for r in baseline if r["observer"] == "global" and r["morphology"]]
    labels = [r["kind"] for r in records] + [primary["kind"]]
    values = [r["validation_loss"] for r in records] + [primary["best_validation_loss"]]
    plt.bar(labels, values)
    plt.yscale("log")
    plt.ylabel("Validation normalized u/v MSE")
    plt.title("Retrospective development selection — no test selection")
    finish("selection")
    plt.figure(figsize=(10, 4))
    for model in (selection["primary"], selection["baseline"], selection["state_only"]):
        result = []
        for seed in sorted({r["seed"] for r in prospective}):
            values = [
                float(r["uv_loss"])
                for r in metric
                if r["model"] == model
                and int(r["seed"]) == seed
                and r["grid"] == "48"
                and r["stratum"] == "all"
            ]
            result.append(np.mean(values))
        plt.plot(sorted({r["seed"] for r in prospective}), result, "o-", label=model)
    plt.yscale("log")
    plt.xlabel("Independent reserved seed family")
    plt.ylabel("Policy-mean normalized u/v MSE")
    plt.legend(fontsize=7)
    plt.title("All reserved families; invalid families remain diagnostic")
    finish("forecasts")
    plt.figure(figsize=(9, 4))
    for model in (selection["primary"], selection["baseline"]):
        values = []
        for h in (0.2, 1.0, 2.0):
            found = [
                float(r["rmse"])
                for r in metric
                if r["model"] == model
                and r["grid"] == "48"
                and r["stratum"].startswith(f"h{h}_")
                and r["stratum"].endswith(("_u", "_v"))
            ]
            values.append(np.mean(found))
        plt.plot((0.2, 1.0, 2.0), values, "o-", label=model)
    plt.xlabel("Forecast horizon (physical time)")
    plt.ylabel("Mean signed-state raw RMSE")
    plt.legend(fontsize=8)
    finish("horizons")
    plt.figure(figsize=(9, 4))
    for kind in ("pca", "17", "23", "29"):
        values = [
            float(r["forecast"]) for r in latentrows if r["kind"] == kind and r["grid"] == "48"
        ]
        plt.bar(kind, np.mean(values))
    plt.yscale("log")
    plt.xlabel("Rank8 PCA or autoencoder training seed")
    plt.ylabel("Prospective normalized latent-decoded forecast MSE")
    finish("latent")
    plt.figure(figsize=(9, 4))
    events = rows(root / "event-oracles.csv")
    actual = [float(r["work_actual"]) for r in events]
    predicted = [float(r["work_prediction"]) for r in events]
    plt.scatter(actual, predicted, s=10, alpha=0.5)
    plt.xlabel("Actual event switching work")
    plt.ylabel("Known-equation pre-event prediction")
    plt.title("Eligibility/clock/work prediction is not a new mechanism")
    finish("work")
    plt.figure(figsize=(9, 4))
    numerical = rows(root / "prospective-numerical.csv")
    plt.bar(
        np.arange(len(numerical)),
        [max(float(r[k]) for k in ("u", "v", "packet", "z", "full_fluid")) for r in numerical],
    )
    plt.axhline(0.1, color="red", linestyle="--", label="10% screen")
    plt.xticks(
        np.arange(len(numerical)),
        [
            r["case"].removesuffix("_P").replace("ADAPTIVE", "A").replace("FIXED", "F")
            for r in numerical
        ],
        rotation=60,
        fontsize=7,
    )
    plt.ylabel("Worst whole-history/field relative discrepancy")
    plt.legend()
    plt.title("Exact palettes/events are additional independent requirements")
    finish("numerical")
    inference = [r for r in metric if r["stratum"] == "recursive_2.0" and r["grid"] == "48"]
    plt.figure(figsize=(9, 4))
    for model in (selection["primary"], selection["baseline"]):
        v = [float(r["uv_loss"]) for r in inference if r["model"] == model]
        if v:
            plt.bar(model, np.mean(v))
    plt.yscale("log")
    plt.ylabel("Recursive10x.2 normalized u/v MSE")
    plt.xticks(fontsize=8)
    plt.title("Unpredicted fluid/traces/controller/palette held fixed")
    finish("recursive")
    training_seconds = (
        sum(r["seconds"] for r in train)
        + sum(r["seconds"] for r in lm)
        + load("training-repeat.json")["seconds"]
    )
    valid = forecast["valid_families"]
    invalid = forecast["invalid_families"]
    compare = forecast["comparisons"]
    primarybase = next(r for r in baseline if r["id"] == selection["baseline"])
    gates = "\n".join(f"| {g} | {forecast[g]} |" for g in ("G1", "G2", "G3", "G4", "G5", "G6"))
    text = f"""# Experiment0013: the external learner — measured results

Registration `c018c65` precedes extraction, fitting and all new outcomes. Instrument
implementation `4a69acb`; held-family evaluation/proposal `08a203d`. Rust remains
physical authority. PyTorch observes and predicts; it never controls the substrate.
Principle002 remains proposed. No overall success score or QR learning/memory claim.

| Separate scientific question | Verdict |
|---|---|
{gates}

## Evidence, dependency and actual execution

Both original QR12 archive hashes pass. All82 historical executions are inventoried,
including2 protocol-invalid intended controls and separate corrective diagnostics.
Historical phases are retrospective. All descendants/refinements/repeats stay in
their physical seed family:401 train,409 validation,419/427 retrospective test.
Thousands of windows/nodes are not independent replications. Duplicates, scalar/
private/oracle cases and numerical invalidity remain explicit in the inventory.
Dataset/metric audits compare compact arrays against actual raw streams, check
horizon alignment, metadata/units, ancestry, invalid labels and family separation.

All32 reserved Rust trajectories actually executed:8 independent new seed families,
FIXED/ADAPTIVE on P/F, unchanged QR12 physics/pulse/SQ, horizon24. Actual case wall
{physical["case_seconds"]:.6f}s; raw case bytes{physical["raw_bytes"]}; peak child RSS
{physical["peak_child_rss_kib"]}KiB. No GPU physics or new physical law. Model/split/
candidate/normalization/checkpoint hashes were sealed BEFORE new execution.
Numerically valid BOTH-policy families:{valid}. Invalid families:{invalid}.
All predictions remain saved; only registered valid family pairs decide gates.
Full state/event agreement, not pretty aggregate plots, determines validity.

## Baselines and external predictive instrument

Persistence, three-lag ridge AR, rank-truncated PCA/linear delay dynamics and a
known-equation frozen-pressure oscillator reduction precede neural fitting. The
PCA delay model is a regularized reduced-rank observable map (DMD-style); its
compact observations are not assumed closed. A separate rank8 PCA latent model
fits ordinary affine8-to8 dynamics. Neither is a separate discovery.
Ordinary spectra/correlations/Hilbert phases retain undefined-pair counts. Exact
full-fluid QR12 composition remains a known accurate unreduced reference.

Selected primary:`{selection["primary"]}`; ordinary comparator:`{selection["baseline"]}`.
Validation normalized u/v losses:{primary["best_validation_loss"]:.9g} versus
{primarybase["validation_loss"]:.9g}. No replacement by best-test model occurred.
All24 forecast fits (MLP/GRU, local/global, palette/state-only,3 training seeds),
three autoencoders and one exact training replay are retained. Total recorded
training time{training_seconds:.6f}s; largest forecast model
{max(r["parameters"] for r in train)}parameters. CPU float32 learner, float64
physics/audit; pinned PyTorch2.15.0+cpu. No CUDA run or GPU compatibility benchmark.
Same-CPU/software repeat parameter tensors and validation predictions agree exactly;
that does not promise cross-platform/version bitwise agreement.

Local features use only own state/history/palette; global features include all
four bodies, current/past global accounts and apparatus forcing kind. Global
accuracy is an external instrument capability, never a neuron's capability.
Forecasts use t-.4,t-.2,t; horizons.2,1,2. Morphology ablation omits explicit
palette, but state/energy/history may already carry structural information.
Input/target normalization/PCA fit only TRAIN401. Validation includes forcing/
geometry regimes absent in training; these are distribution shifts, not evidence
of a new law. Poor external forecasts do not invalidate the physical simulation.

![Actual data partitions](figures/experiment_0013_partitions.png)
![Development selection](figures/experiment_0013_selection.png)
![Reserved family forecasts](figures/experiment_0013_forecasts.png)
![Forecast horizons](figures/experiment_0013_horizons.png)

## G2 forecast and G3 morphology information

Primary mean loss equally averages both policies, nodes and three horizons.
Uncertainty uses independent seed families: exact paired sign-flip p and10000
family bootstrap resamples; no timestamp sample-size inflation. Registered10%
improvement, p<=.05, positive bootstrap lower bound, fine-grid direction and both
training-seed replications are separate requirements. Complete arrays, per-node
signed errors, energy/pressure targets, ordinary/event/accepted-event strata,
recursive10-step error and every failed prediction remain in the evidence.

```json
{json.dumps(compare, indent=2)}
```

Eligibility, occurrence and switching work are separately explained by the
known deterministic local law, apparatus permission and Epost-Epre at unchanged
u/v. Work prediction maximum absolute error:{load("event-oracles.json")["max_work_error"]:.9g}.
No additional scalar neural classifier was registered/trained. Those predictable
labels do not establish learned causal insight. Actual local/remote consequences
are evaluated separately by the palette forecast ablation. The prospective
FIXED/ADAPTIVE comparison changes all eligible nodes; it is not an isolated N0
event intervention. Historical QR12 exact single-event remote size FAIL remains
unchanged. Equal total switch/sham energy never implies identical modal state.

![Known-equation event work](figures/experiment_0013_work.png)
![Numerical verification](figures/experiment_0013_numerical.png)
![Reduced recursive closure](figures/experiment_0013_recursive.png)

## G4 latent structure and observability

Rank8 PCA and autoencoders compare reconstruction, decoded forecast, neural-energy
preservation, event crossings and both grids on the same families. Independent
training-seed latent coordinates are aligned using TRAIN-only affine maps; aligned
errors remain reported rather than interpreted as meaningful modes. Two-step
latent closure is an approximate reduced-model diagnostic, not a functor theorem
or categorical engineering advantage. No latent cluster is called emergence.

```json
{json.dumps(latent, indent=2)}
```

![Actual latent comparison](figures/experiment_0013_latent.png)

## G5 discovery and G6 research efficiency

No candidate met the historical nomination requirements. All3 rejected candidates
and reasons were frozen before final physics. No extra discovery intervention
or independent experiment-selection decision study was executed: G5/G6 NOT RUN.
Inference speed/forecast accuracy is not improved hypothesis selection. There is
no learner-generated new physical mechanism claim. The separate independent
[Codex proposal](EXPERIMENT_0013_CODEX_INDEPENDENT_PROPOSAL.md) argues for an
observability/closure experiment0014, with explicit equal-energy hidden-fluid
controls. Its algebraic rank observation and future hypothesis do not rescue0013
gates or count as prospective discovery. QR12's categorical engineering FAIL remains.

## Limits and next bounded question

Only one historical training seed and one validation seed support instrument
selection, despite many dependent cases. The compact observer omits most fluid
state, and its future is not generally a closed deterministic transition. Shared
kernel two-port sampling, restricted forcing and prescribed event clocks can
produce low-dimensional observations without a novel physical mode. Recursive
forecasts hold unpredicted fluid/trace/controller/palette state fixed; accumulation
and event errors expose that closure assumption. No fitted observer modifies QR
physics; no4096-body, real-material, useful-memory or commercial-performance claim.

Next research requires a new registration: independently excited development
families, explicit missing-fluid-state diagnostics and stronger closure/error
models before larger learners. Preserve all failed forecasts, invalid cases,
rejected hypotheses and historical scientific failures.

## Reproducibility and delivery

Quick Review contains source/docs/figures, complete compact observations, models,
selection/metrics/candidates. Full Evidence adds all new raw fields/streams,
full predictions and the unchanged original QR12 archives as nested ancestry.
Extract BOTH into one directory; `analysis.validate_0013` selectively restores
historical raw paths without overwriting current source, checks member/source/raw
hashes, audits all114 dataset origins and new physical/numerical records, and
re-evaluates sealed models without fitting on tests. See PORTABLE_README.md.
Local strict checks, archive/fresh rebuild/replay, pushed SHA and hosted CI have
separate ignored receipts. Missing receipts remain pending, never scientific PASS.
"""
    (output / "EXPERIMENT_0013_RESULTS.md").write_text(text)
    return forecast


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--output", type=Path, default=Path("docs"))
    a = p.parse_args()
    report(a.root, a.output)


if __name__ == "__main__":
    main()
