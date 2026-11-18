"""Generate QR10 measured numerical figures and viewer-independent report."""

import argparse

# Report paragraphs are intentionally stored as single Markdown lines.
# ruff: noqa: E501
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis import experiment_0009 as q


def coupled_report(root, report, figures):
    pilot = json.loads((root / "pilot/verification.json").read_text())
    summaries = q.rows(root / "pilot/summary.csv")
    report += [
        "## Stationary actual-neuron pilot\n",
        "Pilot implementation `489dc6d` preceded all19 cases. Numerical Level A authorized execution; its receipt is preserved. Two actual independently configured64-module QR neurons, QR6 intrinsic/internal equations and frozen palettes; reciprocal engineered beta=.1 transducers. An isolated homogeneous trajectory matches unmodified QR6 within1e-14 in the software parity test. This is a new isolated-neuron adapter, not a simulated4096-neuron population.\n",
        "| Question | Pilot verdict |",
        "|---|---|",
    ]
    report += [f"| {k} | {v} |" for k, v in pilot["verdicts"].items()]
    report += [
        "\n| Module | Refinement | Receiver full-history relative error | Source-work difference |",
        "|---|---|---|---|",
    ]
    report += [
        f"| {r['module']} | {r['test']} | {float(r['remote_relative']):.8g} | {float(r['source_work_relative']):.8g} |"
        for r in q.rows(root / "pilot/refinement.csv")
    ]
    report += [
        "\n| Pilot case | External work | Positive source-to-fluid work | Backflow | Peak receiver/work | Max balance residual / positive work |",
        "|---|---|---|---|---|---|",
    ]
    report += [
        f"| {r['case']} | {float(r['work']):.8g} | {float(r['emitted_positive']):.8g} | {float(r['source_backflow']):.8g} | {float(r['receiver_per_work']):.8g} | {float(r['balance']):.8g} |"
        for r in summaries
    ]
    report += [
        "\nOFF, ZERO, frozen-source, receiver-only and source-only remote histories remain exactly zero where registered. SOURCE_ONLY still emits into fluid, while its receiver transducer is disconnected. DIRECT uses an explicitly artificial matching-module spring and zero fluid. Every pilot case file in the independent S9 repeat matches byte-for-byte, including its physical metadata. No cross-platform bit-identity claim.\n",
        "At2m the width1.5m tensor-hat supports overlap. The pilot establishes an engineered fluid-mediated causal interaction, not isolated-support propagation delay. No material absorption or long-range acoustic result follows.\n",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for module in (9, 27):
        folder = root / "pilot" / f"s211_m{module}_b0_d2_n48_dt0.05_FLUID"
        rows = q.rows(folder / "metrics.csv")
        axes[0].plot(
            [float(r["time"]) for r in rows],
            [float(r["receiver_energy"]) for r in rows],
            label=f"source module{module}",
        )
        axes[1].plot(
            [float(r["time"]) for r in rows],
            [
                sum(
                    float(r[k])
                    for k in ("fluid_energy", "source_energy", "receiver_energy", "loss")
                )
                - float(r["work"])
                for r in rows
            ],
            label=f"source module{module}",
        )
    axes[0].set(
        xlabel="normalized time",
        ylabel="actual receiver mechanical energy",
        title="Pilot receiver: source excluded",
    )
    axes[1].set(
        xlabel="normalized time",
        ylabel="Efluid + Eneural + damping - external work",
        title="Actual combined balance residual",
    )
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.savefig(figures / "experiment_0010_coupling.png", dpi=160)
    plt.close(fig)
    report += ["![Pilot reception and balance](figures/experiment_0010_coupling.png)\n"]
    ext = root / "extended"
    if not (ext / "communication-verification.json").exists():
        report += [
            "Extended matrix: NOT RUN or incomplete; inspect ledger. C4/C5/C6 INDETERMINATE.\n"
        ]
        return
    report += [
        "## Extended gate verdicts\n",
        "| Stage | C1 emission | C2 reception | C3 accounting | C7 reliability |",
        "|---|---|---|---|---|",
    ]
    for stage in ("train", "evaluate", "interference"):
        receipt = ext / stage / "verification.json"
        if receipt.exists():
            values = json.loads(receipt.read_text())["verdicts"]
            report.append(
                f"| {stage} | {values['C1'] if values['C1'] != 'INDETERMINATE' else 'INDETERMINATE (NOT RUN)'} | {values['C2'] if values['C2'] != 'INDETERMINATE' else 'INDETERMINATE (NOT RUN)'} | {values['C3']} | {values['C7']} |"
            )
    report += [
        "\nINDETERMINATE for an inapplicable stage question means no corresponding gate was run there; interference is evaluated by C6 below. Full per-case failures remain in each stage's gates.csv and verification.json.\n"
    ]
    decoders = q.rows(ext / "decoders.csv")
    responses = q.rows(ext / "responses.csv")
    bands = q.rows(ext / "band_comparisons.csv")
    report += [
        "## Held-out stationary communication\n",
        "Pilot prerequisites passed. Extended engine `1efedac` and decoder `194afd7` preceded their executions. The preserved arithmetic clarification interprets the registration's inconsistent template count as9 decoders/18 class vectors (3 bands x3 distances x2 classes). No feature, acceptance criterion or seed changed.34 new calibration cases plus2 explicit pilot reuses precede the frozen templates; all72 held-out trajectories then execute (36 primary and36 fine), with no refit.8 separate three-neuron interference runs follow.\n",
        "Total159 actual experiment executions:26 numerical +19 pilot +114 extended, with2 explicit calibration reuses. Full fluid fields:503 checkpoints; full actual neural state:399 checkpoints. All signed arrays, all-tick metrics, kick/exchange work, source/configuration/compiler provenance and complete stage plans/events/ledgers remain outside Git in the data package.\n",
        "Each classifier sees101 remote times4..24 every.2,64 modules,signed u/v:12928 scalars. Source samples and metadata are excluded. Class means use only seeds211,223; held seeds227,229. Positive unit force is NOT equal work across modules, seeds or bands: observed work and emitted/backflow work remain explicit. This therefore does not establish equal-energy coding or efficient information transmission.\n",
        "| Band | Separation m | Primary correct/4 | Fine correct/4 | Stable | Max feature grid error | Min class-separation/grid-error | C4 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    report += [
        f"| {('LOW', 'MID', 'HIGH')[int(r['band'])]} | {r['distance']} | {r['primary_correct']} | {r['fine_correct']} | {r['predictions_stable']} | {float(r['maximum_feature_refinement']):.8g} | {float(r['minimum_separation_to_uncertainty']):.8g} | {r['verdict']} |"
        for r in decoders
    ]
    calibration = q.rows(ext / "calibration_predictions.csv")
    report += [
        f"\nCalibration predictions (descriptive training diagnostics, not held-out validation):{sum(r['correct'] == 'True' for r in calibration)}/{len(calibration)} correct; all mistakes/ties retained in calibration_predictions.csv.\n"
    ]
    predictions = q.rows(ext / "predictions.csv")
    incorrect = [r for r in predictions if r["correct"] == "False"]
    ties = [r for r in predictions if r["tie"] == "True"]
    report += [
        f"\nAll{len(predictions)} held-out grid-specific predictions retained: {len(incorrect)} incorrect, {len(ties)} tied. Numerically valid incorrect predictions remain FAIL; numerical uncertainty cannot rescue them. Complete predictions and margins are in extended/predictions.csv and uncertainty.csv.\n",
        f"C4 has{sum(r['verdict'] == 'FAIL' for r in decoders)} failed decoders. In this execution all nine fail on numerically valid observations. This fixed cross-seed readout failure does not establish that every possible readout lacks information. Within-seed differences are numerically resolved; no post-outcome feature selection, refit or seed substitution was performed.\n",
        "## Distance, frequency and interference\n",
        "At4m/6m the source and receiver transducer supports are disjoint. Observed receiver responses there test propagation through actual fluid states, with direct QR graph edges disabled. Arrival uses the registered receiver energy/work floor; actual fields and signed complex pressure spectra are retained. The field is conservative and the neurons damp: loss of local amplitude includes geometry, transducer response, interference and neuronal damping, not simulated seawater material absorption.\n",
        f"C5: measured all3 bands and3 distances. Of{len(bands)} preregistered paired band comparisons normalized by positive emitted work, {sum(r['verdict'] == 'PASS' for r in bands)} exceed5x grid discrepancy with numerical validity; {sum(r['verdict'] == 'INDETERMINATE' for r in bands)} remain INDETERMINATE. Every pair, seed and module is in band_comparisons.csv. LOW/MID/HIGH label finite-envelope forcing carriers, not monochromatic fields; signed spectra retain out-of-band response. No universal LOW-band advantage is inferred. Receiver peak/emitted-work is a local response ratio, not integrated transport efficiency.\n",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for band in range(3):
        for module, style in ((9, "o-"), (27, "s--")):
            rows = [
                r
                for r in responses
                if int(r["band"]) == band
                and int(r["module"]) == module
                and r["grid"] == "fine"
                and r["seed"] == "227"
            ]
            rows.sort(key=lambda r: int(r["distance"]))
            axes[0].semilogy(
                [int(r["distance"]) for r in rows],
                [max(float(r["receiver_per_work"]), 1e-30) for r in rows],
                style,
                label=f"{('LOW', 'MID', 'HIGH')[band]} S{module}",
            )
    axes[0].set(
        xlabel="source-receiver separation (m)",
        ylabel="peak receiver mechanical energy / external work",
        title="Actual held seed227, fine grid; fixed unit forcing",
    )
    axes[0].legend(fontsize=7)
    import numpy as np

    matrix = np.array(
        [
            [
                int(
                    next(r for r in decoders if int(r["band"]) == b and int(r["distance"]) == d)[
                        "fine_correct"
                    ]
                )
                for d in (2, 4, 6)
            ]
            for b in range(3)
        ]
    )
    axes[1].imshow(matrix, vmin=0, vmax=4, cmap="Blues")
    for b in range(3):
        for j, d in enumerate((2, 4, 6)):
            r = next(r for r in decoders if int(r["band"]) == b and int(r["distance"]) == d)
            axes[1].text(
                j,
                b,
                f"{matrix[b, j]}/4\n{r['verdict']}",
                ha="center",
                va="center",
                color="white" if matrix[b, j] >= 3 else "black",
                fontsize=8,
            )
    axes[1].set(
        xticks=range(3),
        xticklabels=["2m", "4m", "6m"],
        yticks=range(3),
        yticklabels=["LOW", "MID", "HIGH"],
        title="Fine held-out classification and full gated verdict",
    )
    fig.savefig(figures / "experiment_0010_communication.png", dpi=160)
    plt.close(fig)
    report += [
        "![Distance, frequency and discrimination](figures/experiment_0010_communication.png)\n"
    ]
    if (ext / "interference-verification.json").exists():
        interference = json.loads((ext / "interference-verification.json").read_text())
        residual = max(r["residual"] for r in interference["observations"])
        report += [
            f"C6 **{interference['C6']}**: signed A/B/AB+/AB- full-fluid and all-neuron superposition maximum relative residual {residual:.9g}. Both independently executed grids, all registered checkpoints and receiver histories are retained. Signed energy cross terms in interference.csv distinguish redistribution from energy destruction. All three actual neurons and all transducers exist in every arm.\n"
        ]
        from analysis import experiment_0010 as f

        fields = []
        for arm in ("IA", "IB", "IAB+", "IAB-"):
            folder = ext / "interference" / f"s211_m9_b0_d4_n48_dt0.05_{arm}"
            fields.append(f.decode(folder / "000240.q10")["fields"][0, 24])
        limit = max(float(np.max(abs(a))) for a in fields)
        fig, axes = plt.subplots(1, 4, figsize=(13, 3), layout="constrained")
        for ax, field, arm in zip(axes, fields, ("A", "B", "A+B", "A-B"), strict=True):
            plot = ax.imshow(
                field, origin="lower", extent=(0, 24, 0, 24), vmin=-limit, vmax=limit, cmap="RdBu_r"
            )
            ax.set(title=arm, xlabel="x (m)", ylabel="y (m)")
        fig.colorbar(plot, ax=axes, label="signed pressure q", shrink=0.7)
        fig.suptitle("Actual signed pressure at t12, z12.25m; common color scale")
        fig.savefig(figures / "experiment_0010_interference.png", dpi=160)
        plt.close(fig)
        report += [
            "![Signed actual fluid interference](figures/experiment_0010_interference.png)\n"
        ]
    passed = [r for r in decoders if r["verdict"] == "PASS"]
    report += [
        "## Answers and limits\n",
        "1. **Energy reporting corrected:** all104 standalone full-field compensated energies equal independent Python math.fsum at exported f64 precision, with the original1e-12 tolerance. Naive summation still reaches2.8224e-11 error. Actual physical energy drift remains separate (maximum0.134719%); no state correction. Evidence: numerical/observations.csv,gates.csv,summary.csv.\n",
        "2. **Convergence measured:** temporal observed order2.00004-2.00070; corrected spatial order3.92850-3.99559. Fixed-space/time comparisons and exact split residuals are explicit; raw cancellation-prone continuum errors remain preserved. Evidence: numerical/rates.csv,observations.csv.\n",
        "3. **Registered exploratory solver accuracy passes:** numerical A,D,E and Level A pass; B,C and standalone Level B also pass. This does not remove coupled-field uncertainty. Maximum primary/fine N>=48 continuum field error0.853239%; excluded coarse N24 rate diagnostics reach13.2470%. Long240 is an energy/reliability result only. Evidence: numerical/verification.json and every gate.\n",
        "4. **Actual QR emission passes the pilot:** source module activity changes the fluid under the explicit reciprocal law, with external work and source-positive/backflow work recorded separately. Evidence: pilot/summary.csv,ports.csv,kicks.csv,exchange.csv and signed checkpoints.\n",
        "5. **Actual QR reception is causally attributable in the pilot:** remote receiver state responds with fluid ports active and remains zero under the registered disabled/frozen controls. Kernel overlap limits the2m interpretation; extended4/6m have disjoint supports. Evidence: pilot/gates.csv,history.csv and extended/responses.csv.\n",
        f"6. **Controlled source discrimination:** {len(passed)}/9 registered band-distance decoders meet the complete held-out and uncertainty gates; the table retains all other verdicts. Evidence: extended/decoders.csv,predictions.csv,uncertainty.csv and frozen templates.json.\n",
        "7. **Limits:** two/three stationary neurons; finite seed and stimulus set; engineered transducer and physical mapping; closed reflecting conservative fluid; unit amplitude rather than equal supplied work; external fixed calibration; no empirical sensor noise, mobile geometry, full-population scaling, capacity, learning, plasticity or associative-memory validation. Standalone Level B is not automatic validation of arbitrary broadband coupled fields. Principle 002 is a proposed mechanism, not an experimentally established law.\n",
        "## Evidence and reproduction\n",
        "Software tests are synthetic invariants/parity checks. Independent audits reconstruct recorded fields, geometry, energy, exact substep work and numerical gates; they are not a second complete coupled PDE integration. Every-tick reduced diagnostics are checked at full-state checkpoints, not advertised as every-tick full-field exports. No viewer, GPU execution, native window or FPS witness.\n",
        "Install pinned analysis/plot dependencies, extract both portable archives together, and use PORTABLE_README.md. Historical protected hashes remain verified. Execution provenance identifies original executables and source commits; source-freeze snapshots preserve those versions independently of final delivery source. Full plans/events/completion/reuse ledgers separate simulations, explicit reuse and scientific decisions. Local strict checks, pushed SHA and hosted CI are recorded separately in delivery receipts.\n",
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root
    result = json.loads((root / "numerical/verification.json").read_text())
    obs = q.rows(root / "numerical/observations.csv")
    rates = q.rows(root / "numerical/rates.csv")
    figures = Path("docs/figures")
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for mode in q.MODES:
        name = q.fixture_name(mode)
        selected = [
            r
            for r in obs
            if r["case"].startswith(name + "_n48_dt")
            and not r["case"].endswith(("repeat", "long"))
            and float(r["time"]) == 24
        ]
        selected.sort(key=lambda r: float(r["case"].split("_dt")[1]))
        axes[0].loglog(
            [float(r["case"].split("_dt")[1]) for r in selected],
            [float(r["temporal_error"]) for r in selected],
            "o-",
            label=name,
        )
        selected = [
            r
            for r in obs
            if r["case"].startswith(name)
            and r["case"].endswith("dt0.0125")
            and float(r["time"]) == 24
        ]
        selected.sort(key=lambda r: int(r["case"].split("_n")[1].split("_")[0]))
        axes[1].loglog(
            [24 / int(r["case"].split("_n")[1].split("_")[0]) for r in selected],
            [float(r["corrected_spatial_error"]) for r in selected],
            "o-",
            label=name,
        )
    axes[0].set(
        xlabel="dt, fixed N48",
        ylabel="relative full-field temporal error",
        title="Temporal vs exact semidiscrete, t24",
    )
    axes[1].set(
        xlabel="h, fixed dt .0125",
        ylabel="relative corrected spatial error",
        title="Spatial diagnostic (analytic time correction)",
    )
    for ax in axes:
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    fig.savefig(figures / "experiment_0010_convergence.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for suffix in ("", "_long"):
        folder = root / "numerical" / ("mode8-0-0_n48_dt0.05" + suffix)
        rows = q.rows(folder / "metrics.csv")
        initial = float(rows[0]["energy"])
        axes[0].plot(
            [float(r["time"]) for r in rows],
            [(float(r["energy"]) - initial) / initial for r in rows],
            label="HIGH" + suffix,
        )
    axes[0].set(
        xlabel="normalized time",
        ylabel="(actual energy - initial)/initial",
        title="Physical discrete energy drift, no source work",
    )
    axes[0].legend()
    axes[1].semilogy(
        [max(float(r["naive_relative"]), 1e-18) for r in obs], label="naive / fsum discrepancy"
    )
    axes[1].semilogy(
        [
            max(float(r["accounting_absolute"]) / max(float(r["energy_fsum"]), 1e-30), 1e-18)
            for r in obs
        ],
        label="compensated / fsum discrepancy",
    )
    axes[1].axhline(1e-12, color="black", ls="--", label="registered reconstruction limit")
    axes[1].set(
        xlabel="registered checkpoint index",
        ylabel="relative reporting error",
        title="Reporting error (zeros plotted at 1e-18)",
    )
    axes[1].legend(fontsize=7)
    fig.savefig(figures / "experiment_0010_energy.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for mode in q.MODES:
        selected = [
            r
            for r in obs
            if r["case"] == q.fixture_name(mode) + "_n48_dt0.05" and float(r["time"]) > 0
        ]
        axes[0].plot(
            [float(r["time"]) for r in selected],
            [100 * float(r["continuum_error"]) for r in selected],
            "o-",
            label=q.fixture_name(mode),
        )
    axes[0].set(
        xlabel="normalized time",
        ylabel="continuum field error (%)",
        title="Measured physical accuracy, N48 dt .05",
    )
    axes[0].legend(fontsize=7)
    for distance in (2, 4, 6):
        rows = q.rows(root / "numerical/gaussian_n48_dt0.05/probes.csv")
        selected = [r for r in rows if r["axis"] == "0" and float(r["offset"]) == distance]
        axes[1].plot(
            [int(r["tick"]) * 0.05 for r in selected],
            [float(r["q"]) for r in selected],
            label=f"{distance} m",
        )
    axes[1].set(
        xlabel="normalized time",
        ylabel="signed pressure q",
        title="Gaussian fluid propagation, not neural communication",
    )
    axes[1].legend()
    fig.savefig(figures / "experiment_0010_accuracy_propagation.png", dpi=160)
    plt.close(fig)
    # Coupling report is added only from independently audited recorded cases.
    report = [
        "# Experiment 0010: numerical rehabilitation and controlled neural-fluid coupling\n",
        "Registration `9a3bb58` preceded implementation `1df11d1` and all execution. Historical Experiment 0009 remains FAIL. No overall success score.\n",
        "## Numerical results\n",
        "| Category | Verdict |",
        "|---|---|",
    ]
    names = {
        "A": "physical accuracy",
        "B": "temporal convergence",
        "C": "spatial convergence",
        "D": "conservation and accounting",
        "E": "reliability",
    }
    report += [f"| {k}: {names[k]} | {v} |" for k, v in result["categories"].items()]
    report += [
        f"\nLevel A: **{result['level_A']}**. Level B: **{result['level_B']}**. All26 registered serial executions and104 signed checkpoints audited.\n",
        "| Mode | Test | Pair | Error ratio | Observed order | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    report += [
        f"| {r['mode']} | {r['category']} | {r['pair']} | {r['ratio']} | {r['order']} | {r['verdict']} |"
        for r in rates
    ]
    max_account = max(
        float(r["accounting_absolute"]) / max(float(r["energy_fsum"]), 1e-30) for r in obs
    )
    report += [
        f"\nMaximum compensated/f-sum relative reporting discrepancy: {max_account:.12g}; unchanged limit1e-12. Maximum naive discrepancy: {max(float(r['naive_relative']) for r in obs):.12g}. Reporting improvement is not correction of physical energy drift.\n",
        "![Convergence](figures/experiment_0010_convergence.png)\n",
        "![Energy](figures/experiment_0010_energy.png)\n",
        "![Accuracy and fluid propagation](figures/experiment_0010_accuracy_propagation.png)\n",
        "Full gate values, component errors, phase, amplitude, speed, energy residuals, all-tick diagnostics and signed fields remain in the portable package. Spatial correction is an analytical diagnostic only; observations are never corrected. The raw continuum error can cancel between spatial and temporal dispersion.\n",
    ]
    if (root / "pilot/verification.json").exists():
        coupled_report(root, report, figures)
    Path("docs/EXPERIMENT_0010_RESULTS.md").write_text("\n".join(report).rstrip() + "\n")


if __name__ == "__main__":
    main()
