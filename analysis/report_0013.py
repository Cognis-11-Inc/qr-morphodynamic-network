"""Measured QR13 figures and separate results/exploitation reports, never synthetic data."""

# Markdown report paragraphs intentionally remain complete source lines.
# ruff: noqa: E501

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
        color=["#d95f02" if int(r["event_pattern_disagree"]) else "#377eb8" for r in numerical],
    )
    plt.axhline(0.1, color="red", linestyle="--", label="10% screen")
    plt.xticks(
        np.arange(len(numerical)),
        [
            r["case"].removesuffix("_P").replace("ADAPTIVE", "A").replace("FIXED", "F")
            + ("*" if int(r["event_pattern_disagree"]) else "")
            for r in numerical
        ],
        rotation=60,
        fontsize=7,
    )
    plt.ylabel("Worst whole-history/field relative discrepancy")
    plt.legend()
    plt.title("* = event/palette mismatch: invalid despite small continuous error")
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
    plt.figure(figsize=(9, 4))
    with np.load(root / "data/QR13__s431_FIXED_F.npz") as a:
        velocity = a["v"][:, :, 9]
        frequency = np.fft.rfftfreq(len(velocity), 0.2)
        power = abs(np.fft.rfft(velocity, axis=0)) ** 2
        for node in range(4):
            positive = power[:, node] > 0
            plt.semilogy(frequency[positive], power[positive, node], label=f"N{node}")
    plt.xlabel("Frequency / normalized physical time")
    plt.ylabel("Actual module9 velocity FFT power")
    plt.legend()
    plt.title("Reserved431 FIXED fine grid; no synthetic modes")
    finish("spectra")
    training_seconds = (
        sum(r["seconds"] for r in train)
        + sum(r["seconds"] for r in lm)
        + load("training-repeat.json")["seconds"]
    )
    valid = forecast["valid_families"]
    invalid = forecast["invalid_families"]
    compare = forecast["comparisons"]
    primarybase = next(r for r in baseline if r["id"] == selection["baseline"])
    collision = load("post-outcome-observability.json")
    stability = next(
        r
        for r in load("prediction-stability.json")["records"]
        if r["model"] == selection["primary"]
    )
    stability_text = (
        f"All {stability['finite_cases']} primary cases have finite predictions; "
        f"{stability['negative_energy_predictions']}of"
        f"{stability['energy_predictions']}predicted energies are negative. "
        "These are external prediction defects, never changes to physical state."
    )
    names = dict(
        G1="Dataset integrity",
        G2="Predictive utility",
        G3="Morphology information",
        G4="Latent structure",
        G5="Prospective discovery",
        G6="Research efficiency",
    )
    gates = "\n".join(f"| {g}: {names[g]} | {forecast[g]} |" for g in names)
    role_table = "| Model | Horizon | N0 u/v RMSE | N1 u/v RMSE | N2 u/v RMSE | N3 u/v RMSE |\n"
    role_table += "|---|---|---|---|---|---|\n"
    for model, label in ((selection["primary"], "MLP"), (selection["baseline"], "Linear")):
        for horizon in (0.2, 1.0, 2.0):
            values = []
            for node in range(4):
                errors = [
                    float(r["rmse"]) ** 2
                    for r in metric
                    if r["model"] == model
                    and int(r["seed"]) in valid
                    and r["grid"] == "48"
                    and r["stratum"] in (f"h{horizon}_N{node}_u", f"h{horizon}_N{node}_v")
                ]
                values.append(float(np.sqrt(np.mean(errors))))
            role_table += (
                f"| {label} | {horizon} | " + " | ".join(f"{v:.7g}" for v in values) + " |\n"
            )
    headline = (
        f"On {len(valid)} valid prospective families, the selected MLP has"
        f"{-100 * compare['G2']['primary']['relative_improvement']:.1f}% higher u/v MSE"
        " than the selected linear baseline. Explicit palette input has"
        f"{-100 * compare['G3']['primary']['relative_improvement']:.1f}% higher event-window loss."
        f" The autoencoder's reconstruction/latent forecast losses are"
        f"{-100 * latent['comparisons']['reconstruction']['primary']['relative_improvement']:.1f}%/"
        f"{-100 * latent['comparisons']['forecast']['primary']['relative_improvement']:.1f}% higher"
        " than PCA. These are results for this registered instrument/data budget,"
        " not a general rejection of machine learning or QR physics."
    )
    text = f"""# Experiment0013: the external learner — measured results

Registration `c018c65` precedes extraction, fitting and all new outcomes. Instrument
implementation `4a69acb`; held-family evaluation/proposal `08a203d`. Rust remains
physical authority. PyTorch observes and predicts; it never controls the substrate.
Principle002 remains proposed. No overall success score or QR learning/memory claim.

| Separate scientific question | Verdict |
|---|---|
{gates}

{headline}

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
Ordinary spectra/correlations/Hilbert phases retain undefined-pair counts. Rank8
PCA explains96.115% of TRAIN normalized-state variance, not held-out variance. Exact
full-fluid QR12 composition remains a known accurate unreduced reference.

Selected primary:`{selection["primary"]}`; ordinary comparator:`{selection["baseline"]}`.
Validation normalized u/v losses:{primary["best_validation_loss"]:.9g} versus
{primarybase["validation_loss"]:.9g}. No replacement by best-test model occurred.
All24 forecast fits (MLP/GRU, local/global, palette/state-only,3 training seeds),
three autoencoders and one exact training replay are retained. Total recorded
training time{training_seconds:.6f}s; largest forecast model
{max(r["parameters"] for r in train)}parameters. CPU float32 learner, float64
physics/audit; pinned PyTorch2.15.0+cpu. No CUDA run or GPU compatibility benchmark.
One cost-only benchmark extension stopped on a missing-variable NameError; its
log is retained as cost-benchmark-failed.log. The instrumentation was corrected
before expanded timings; models, physical data, predictions and gates were unchanged.
Inference costs are recorded in inference-costs.json: end-to-end CPU prediction
includes normalization/model loading. The baseline uses a dense exported matrix,
not optimized low-rank factors; these timings establish no algorithmic speed
superiority or hypothesis-selection efficiency.
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
{stability_text}

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

Actual primary-grid per-node signed-state forecast errors on valid families
(equal case/coordinate averaging; descriptive, not extra independent samples):

{role_table}

N0 is externally driven; N1/N2/N3 are externally unforced. These errors are not
single-event causal effect sizes. The final24-unit event changes palette/energy
but has no subsequent u/v evolution in this window; u/v event-consequence evidence
therefore comes from the16-unit event and intervals after it. The horizon choice
cannot establish the consequences of the final switch. This limitation does not
change the preregistered event-window gate.

## G4 latent structure and observability

Rank8 PCA and autoencoders compare reconstruction, decoded forecast, neural-energy
preservation, event crossings and both grids on the same families. Independent
training-seed latent coordinates are aligned using TRAIN-only affine maps; aligned
errors remain reported rather than interpreted as meaningful modes. Two-step
latent closure is an approximate reduced-model diagnostic, not a functor theorem
or categorical engineering advantage. No latent cluster is called emergence. Latent-coordinate closure errors depend
on the encoder coordinate gauge; decoded physical forecast/reconstruction losses
are the meaningful cross-representation comparisons.

```json
{json.dumps(latent, indent=2)}
```

![Actual latent comparison](figures/experiment_0013_latent.png)
![Actual held-out spectrum](figures/experiment_0013_spectra.png)

## Post-outcome observation-interface diagnostic

This retrospective diagnostic was added AFTER final evaluation, not selected from
historical development and not a G5 discovery. The registered observer omits the
external FIXED/ADAPTIVE permission policy. Before the first switch, each paired
run has identical supplied features/palette but13 horizon labels later differ
in u/v. The simulator remains deterministic given complete state AND control.
Metadata retains the policy, so dataset origin/integrity is not ambiguous.

For identical inputs with equally weighted targets a,b, the best squared-loss
prediction is(a+b)/2 and irreducible policy-average error is(a-b)^2/4. The measured
valid-family normalized u/v floor is{collision["valid_family_mean_normalized_uv_floor"]:.9g},
only{100 * collision["fraction_of_selected_baseline_error"]:.6f}% of the selected
baseline's error. This omission is real but much too small to explain the51.3%
neural performance gap. No inputs, models, normalizers or gates were repaired.
Full paired counts/times/grids remain in post-outcome-observation-collisions.csv.

Distinct physical arrows/commands should remain distinguishable in a future
control-conditioned global observer. This is an ordinary state-space modeling
requirement; it confers no categorical engineering premium. The independent
proposal separates this diagnostic from the original hidden-fluid closure idea.

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


def exploitation(root, output):
    root, output = Path(root), Path(output)
    verdict = json.loads((root / "scientific-verdicts.json").read_text())
    physical = json.loads((root / "physical-execution.json").read_text())
    train = json.loads((root / "training.json").read_text())
    latent = json.loads((root / "latent-models.json").read_text())
    cost = sum(r["seconds"] for r in train + latent)
    candidates = [
        (
            "Scientific observation and diagnostics",
            "PURSUE — internal reuse",
            "Provenance-bound114-execution inventory, family splits, exact raw/compact alignment, event/work oracles and forecast audits.",
            "Existing QR12 raw readers/audits and ordinary manual analysis already verify physics; QR13 adds an external instrument boundary, not a new physical law.",
            "G1 integrity passes; no measured speed or diagnostic-yield advantage over the prior workflow. G2/G4 results stay separate.",
            "Only four-body stationary normalized physics and a few historical development families; external observer information is not local neuron capability.",
            "External-lab reproduction and deliberately corrupted/misaligned real dataset trials beyond software fixtures.",
            "A research software engineer inspecting hybrid-system recordings.",
            "Open one actual trajectory, show source hashes/ancestry, forecast origins, invalid labels and independent loss reconstruction.",
        ),
        (
            "Reduced-order simulation",
            "INVESTIGATE FURTHER" if verdict["G2"] == "PASS" else "DEFER",
            "Small frozen local/global MLP/GRU forecasts at.2/1/2 units, with complete held errors, rollout accumulation and training replicas.",
            "Matched persistence, ridge, reduced linear delay maps, rank8 PCA dynamics and known-equation oscillator reduction; exact full-fluid composition remains the unreduced reference.",
            "Predictive utility G2="
            + verdict["G2"]
            + "; no demonstrated replacement for the authoritative solver or full fluid.",
            "Restricted pulse/SQ test distribution; unobserved fluid, prescribed morphology and one historical training family limit transfer. Energy conservation is not enforced by the learned predictor.",
            "Diverse independent development seeds, forcing/geometry transfer, calibrated error bounds and a controlled accuracy/runtime solver benchmark.",
            "A dynamics researcher needing a bounded preview or error diagnostic, not a physical-law replacement.",
            "Replay a reserved fixed/adaptive case with all horizons, pressure/energy errors and the strongest ordinary comparator.",
        ),
        (
            "Hybrid dynamical-system analysis",
            "INVESTIGATE FURTHER",
            "Ordinary/learned representation comparisons with exact event boundaries, work accounts, numerical-pair labels and decoded physical observables.",
            "PCA, fixed-palette linear mechanics, spectral/correlation/phase analysis and known local event rules.",
            "G3="
            + verdict["G3"]
            + ", G4="
            + verdict["G4"]
            + ". Deterministic eligibility/permission/work already explains event labels; no new mode/mechanism is established.",
            "A latent coordinate need not be a mode; compact state need not be Markov. Different policies change multiple nodes, so their contrast is not a single-event causal attribution.",
            "The separately proposed equal-energy hidden-fluid closure test and excitation-weighted observability diagnostics require fresh registration.",
            "An engineer studying switched oscillators or coupled multiphysics reductions.",
            "An actual pre/post event, exact work oracle, refined local/remote difference and PCA-versus-latent error table.",
        ),
        (
            "Automated research instrumentation",
            "INVESTIGATE FURTHER",
            "Frozen development selection, model/data/source hashes, rejected-candidate registry, independent physical validation and reproducible report generation.",
            "Ordinary registered scripts and human interpretation can perform the same tasks; automation alone is not scientific discovery.",
            "G5 NOT RUN: no candidate met the nomination criteria. No automated discovery or better hypothesis yield is measured.",
            "Only a bounded three-candidate nomination procedure was exercised; its false negatives and decision quality are unknown.",
            "A blinded candidate pool with independent physical outcomes and a registered human/simple-statistical comparison.",
            "A small laboratory maintaining reproducible numerical investigations.",
            "Run the sealed workflow and show a rejected hypothesis remains rejected after the held outcomes, without retuning.",
        ),
        (
            "Efficient experiment selection",
            "DEFER",
            "Training/analysis costs and the fixed32-case prospective budget are recorded; all3 historical candidates were rejected before outcomes.",
            "A fixed preregistered matrix or simpler ranking rule is the relevant decision baseline, not merely slow neural inference.",
            "G6 NOT RUN. No independent experiment-selection decision study occurred, so no efficiency improvement is claimed.",
            "Forecast inference speed does not measure physical-validation yield; zero qualified nominations does not estimate false-negative rates.",
            "At least8 independent prospective decisions, equal candidate budgets and measured valid yield per total compute-second.",
            "A researcher with expensive future experiments and a controlled candidate pool.",
            "A separately registered small selection study comparing learner, linear ranking and fixed sampling on identical candidates.",
        ),
        (
            "Reproducible scientific machine learning",
            "PURSUE — internal reuse",
            "CPU-capable small models, grouped leakage controls, training/checkpoint hashes, same-environment repeat, complete failed predictions and portable raw ancestry.",
            "Ordinary reproducibility practice and the prior QR12 independent-physics archive, rather than a categorical or proprietary premium.",
            "Same CPU/software repeat is exact; all quantitative predictive/latent verdicts are reported even when unfavorable. No cross-platform bitwise promise or external-user advantage.",
            "Original execution used one workstation and pinned CPU torch. CUDA compatibility/performance and broader data sources are untested.",
            "Fresh-extraction receipts, external/platform reproduction, dependency lifecycle support and independent user trials.",
            "A research engineer publishing an inspectable negative or mixed ML study.",
            "Extract both archives, rebuild Rust, reconstruct raw alignment and re-evaluate frozen weights without training on tests.",
        ),
        (
            "Developer tools and research services",
            "INVESTIGATE FURTHER",
            "Dataset inspectors, exact event/work checks, grouped forecast evaluation and a portable research report pipeline.",
            "Existing general scientific Python tools and conventional research engineering; no customer/competitive study exists.",
            "Reusable engineering is concrete, while performance, commercial demand and a paid-service advantage are unmeasured.",
            "The API is specific to QR12 formats/four bodies and the current scientific workflow. No production interface, support commitment or material/hardware model is established.",
            "A clear supported interface, license/disclosure assessment, maintenance budget and independently requested user evaluation.",
            "A numerical-research team needing traceable analysis of its own lawful simulator.",
            "A documented CLI inspection/audit service over a single complete supplied recording, with limitations and cost receipts.",
        ),
    ]
    text = "# Experiment0013 — evidence-based research exploitation assessment\n\n"
    text += (
        "This is a bounded technical assessment, not marketing, legal/IP advice or "
        "a demand forecast. Rust supplies physical evidence; the external learner supplies "
        "testable predictions. No global success score.\n\n"
    )
    text += (
        f"Measured context:32 prospective physical trajectories, "
        f"{physical['case_seconds']:.3f}s case wall and{physical['raw_bytes']}raw bytes; "
        f"24 forecast fits +3 autoencoders used{cost:.3f}s recorded fitting time, "
        "plus the separately recorded repeat, baseline and analysis costs. "
        "Both original QR12 archives and all raw/model/selection hashes are retained. "
        "Fresh validation, push and hosted-CI receipts remain separate.\n\n"
    )
    for number, (
        title,
        priority,
        capability,
        baseline,
        advantage,
        limit,
        missing,
        user,
        demo,
    ) in enumerate(candidates, 1):
        text += f"## {number}. {title} — {priority}\n\n"
        for label, value in (
            ("1. Verified capability", capability),
            ("2. Baseline comparison", baseline),
            ("3. Measured advantage", advantage),
            (
                "4. Computational and implementation costs",
                "The measured context above includes training and physical data acquisition; the pinned CPU/NumPy/PyTorch reader/model/audit pipeline must also be maintained. No labor-cost, solver-speed or revenue estimate is invented.",
            ),
            ("5. Generalization limits", limit),
            ("6. Missing validation", missing),
            (
                "7. Possible practical user",
                user + " This names a role, not an identified customer.",
            ),
            ("8. Smallest credible demonstration", demo),
            (
                "9. Publication opportunity",
                "A transparent methods/negative-results study with independent reproduction, grouped uncertainty, strong baselines and every invalid/rejected result. Novelty/prior-art review remains necessary; software correctness alone is not a new physical mechanism.",
            ),
            (
                "10. Commercial investigation priority",
                priority
                + ". No demand, patentability, exclusivity, competitive superiority or product readiness has been established.",
            ),
        ):
            text += f"**{label}.** {value}\n\n"
    text += (
        "The immediate defensible value is a reproducible scientific instrument and "
        "a documented comparison with simpler methods. Forecast success would remain "
        "distinct from explanation; the actual G1..G6 verdicts and independent proposal "
        "determine the next registered question.\n"
    )
    (output / "EXPERIMENT_0013_EXPLOITATION.md").write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--output", type=Path, default=Path("docs"))
    a = p.parse_args()
    report(a.root, a.output)
    exploitation(a.root, a.output)


if __name__ == "__main__":
    main()
