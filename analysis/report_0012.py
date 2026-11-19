"""Measured QR12 figures, complete coverage and separate scientific/exploitation reports."""

# Markdown paragraphs are intentionally complete lines.
# ruff: noqa: E501
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis import io_0012 as io
from analysis.experiment_0009 import csv_write, rows
from analysis.gates_0012 import uv
from analysis.plan_0012 import plan


def load(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else None


def coverage(root):
    root = Path(root)
    out = []
    wall = 0.0
    raw = 0
    complete = 0
    for stage in "abcde":
        actual = (
            {r["case"]: r for r in rows(root / stage / "ledger.csv")}
            if (root / stage / "ledger.csv").exists()
            else {}
        )
        for expected in plan(root, stage):
            name = expected["case"]
            row = actual.get(name)
            status = row["status"] if row else "NOT RUN"
            seconds = float(row["elapsed_seconds"]) if row else 0.0
            condition_status = "VALID" if row else "NOT RUN"
            if (
                row
                and expected["policy"] != rows(root / stage / name / "metadata.csv")[0]["policy"]
            ):
                condition_status = "PROTOCOL_INVALID"
            out.append(
                dict(
                    stage=stage,
                    case=name,
                    status=status,
                    condition_status=condition_status,
                    seconds=seconds,
                    reason=""
                    if row
                    else "Not executed; consult prerequisite and stopping receipts.",
                )
            )
            if row:
                wall += seconds
                complete += int(status == "COMPLETE")
                raw += sum(p.stat().st_size for p in (root / stage / name).iterdir() if p.is_file())
    assert len(out) == 80 and wall < 3600 and raw < 16_000_000_000
    diagnostic_count = 0
    diagnostic = root / "diagnostic_nonadaptive"
    if (diagnostic / "ledger.csv").exists():
        for item in rows(diagnostic / "ledger.csv"):
            seconds = float(item["elapsed_seconds"])
            out.append(
                dict(
                    stage="diagnostic_nonadaptive",
                    case=item["case"],
                    status=item["status"],
                    condition_status="POST_OUTCOME_DIAGNOSTIC",
                    seconds=seconds,
                    reason="Separate preregistered control-completion diagnostic; does not replace original observations.",
                )
            )
            wall += seconds
            raw += sum(
                p.stat().st_size for p in (diagnostic / item["case"]).iterdir() if p.is_file()
            )
            diagnostic_count += 1
    assert wall < 3600 and raw < 16_000_000_000
    csv_write(root / "EXECUTION_LEDGER.csv", out)
    r = dict(
        diagnostic_trajectories=diagnostic_count,
        total_actual_trajectories=complete + diagnostic_count,
        original_protocol_invalid=sum(x["condition_status"] == "PROTOCOL_INVALID" for x in out),
        original_valid_conditions=sum(x["condition_status"] == "VALID" for x in out),
        actual_trajectories=complete,
        not_run=sum(x["status"] == "NOT RUN" for x in out),
        registered_maximum=80,
        physical_case_seconds=wall,
        raw_case_bytes=raw,
        full_checkpoints=sum(
            1 for s in (*"abcde", "diagnostic_nonadaptive") for p in (root / s).glob("*/*.q12")
        )
        + sum(1 for p in (root / "a").glob("*/*.q11")),
        every_tick_streams=complete + diagnostic_count,
    )
    (root / "EXECUTION_RECEIPT.json").write_text(json.dumps(r, indent=2) + "\n")
    return r


def document(root):
    root = Path(root)
    receipt = coverage(root)
    figdir = Path("docs/figures")
    figdir.mkdir(exist_ok=True)
    a = load(root / "a/gates.json")
    b = load(root / "b/gates.json")
    c = load(root / "causal-verification.json")
    d = load(root / "collective-verification.json")
    e = load(root / "composition-verification.json")
    formal = load(root / "formal-verification.json")
    table = [
        ("A extended numerical prerequisite", a["A"] if a else "NOT RUN"),
        ("M1 repeated morphology", b["M1_activity"] if b else "NOT RUN"),
        ("M1 refined event/dynamic validity", b["M1_validity"] if b else "NOT RUN"),
        ("M1 dynamical consequence", b["M1_consequence"] if b else "NOT RUN"),
    ]
    table += [
        (k, c[k] if c else "NOT RUN")
        for k in ("M2_activity_to_morphology", "M2_local", "M2_remote", "M2_permit_vs_energy_sham")
    ]
    table += [
        (k, d[k] if d else "NOT RUN")
        for k in (
            "M3_reciprocal_collective",
            "M3_morphological_modulation",
            "M3_increased_diversity",
        )
    ]
    table += [
        (
            k,
            (formal if k in ("MATHEMATICAL_VALIDITY", "ENGINEERING_UTILITY") else e)[k]
            if (formal if k in ("MATHEMATICAL_VALIDITY", "ENGINEERING_UTILITY") else e)
            else "NOT RUN",
        )
        for k in (
            "MATHEMATICAL_VALIDITY",
            "PHYSICAL_AGREEMENT",
            "PREDICTIVE_UTILITY",
            "ENGINEERING_UTILITY",
        )
    ]
    text = [
        "# Experiment 0012: the morphodynamic network",
        "",
        "Registration94285ca precedes implementation d548de4 and every QR12 physical outcome. Project branding baseline52e4dba preserves all historical registrations and evidence. Principle002 remains a proposed mechanism, not an experimentally established law. No learning, memory, recognition or intelligence success criterion. No overall success score.",
        "",
        "| Separate question | Verdict |",
        "|---|---|",
    ] + [f"| {name} | {verdict} |" for name, verdict in table]
    text += [
        "",
        "## Coverage and methodological boundaries",
        "",
        f"{receipt['actual_trajectories']} original actual trajectories ({receipt['original_valid_conditions']} valid intended conditions, {receipt['original_protocol_invalid']} protocol-invalid controls), plus{receipt['diagnostic_trajectories']} separate diagnostics; {receipt['not_run']} original trajectories never started; {receipt['full_checkpoints']} signed full-field checkpoints; every actual physical tick retains all instantiated nodes,405 traces and local controllers. Actual physical-case wall{receipt['physical_case_seconds']:.6f}s and raw case bytes{receipt['raw_case_bytes']} remain within3600s/16GB. Complete80-condition ledger plus separate diagnostics, exact plans, source/compiler/executable provenance and raw integrity manifests remain outside Git.",
        "",
        "Four genuine8x8 QR neurons share one unchanged QR10 fluid state. They use QR11 intrinsic/cardinal equations, mass1, damping and two reciprocal ports each. Source roles are apparatus designations. Positions form the registered4m square; the ALT6m square and private-fluid/simpler-oscillator controls are separately labeled. Internal controller proposals receive only own palette,u/v,packet,traces and clock/history. No direct graph/message bus or decoder supplies a response.",
        "",
        "Morphology is explicitly activity-gated at local opportunities16,24,32, max3 one-edge swaps per neuron,8-unit refractory and hysteresis. No minimum changes are forced. This bounded candidate is not autonomous indefinite plasticity. Switching work is an external energetic intervention, not free energy. Read-only computational traces do not include a model of physical storage/computation cost.",
        "",
        "## Preserved verifier and observability corrections",
        "",
        "[Execution clarifications](EXPERIMENT_0012_EXECUTION_CLARIFICATIONS.md) preserve both original defects and original failed/incorrect audit receipts. Original-QR11 oracle source-only transfer was mislabeled port_net by the observer adapter; the verifier now explicitly interprets that legacy column while still auditing every actual port and total balance. No raw data or trajectory was changed. A later relative-effect verifier mistakenly subtracted a baseline twice; its correction retains the registered0.1% effect threshold and yields M2_remote FAIL. A targeted regression invariant rejects this error. No seed, input, numerical threshold or physical model was tuned. Original failed/incorrect receipts remain in post-outcome-* directories. The unavailable external time wrapper caused no physical case to start; C/D resource measurement used Python getrusage instead.",
        "",
        "## M1: ongoing local morphology",
        "",
    ]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
    for j, label in enumerate(("ADAPTIVE_P", "VETO_ALL_P")):
        folder = root / "b" / label
        if folder.exists():
            r = rows(folder / "metrics.csv")
            time = np.array([float(x["time"]) for x in r])
            for i in range(4):
                en = np.array([float(x["e" + str(i)]) for x in r])
                ax[j].plot(time, np.ma.masked_less_equal(en, 0), label=f"N{i}")
            ax[j].set(
                yscale="log",
                xlabel="normalized time",
                ylabel="actual node mechanical energy",
                title=label,
            )
            ax[j].legend()
    fig.savefig(figdir / "experiment_0012_activity.png", dpi=150)
    plt.close(fig)
    text += ["![Actual individual energy](figures/experiment_0012_activity.png)", ""]
    if b:
        text += [
            f"All registered pilot counts P/F: {b['event_counts']}. Exact accepted-event patterns and all actual palettes agree across P/T/F; numerical gates and every event work/eligibility record remain in b/gates.csv,events.csv,scores.csv,audit.json. Adaptive-veto signed difference norm{b['consequence_norm']:.9g}, grid discrepancy{b['consequence_grid_error']:.9g}.",
            "",
            "| Node | Successful events P | Unique observed palettes P |",
            "|---|---|---|",
        ]
        s = io.stream(root / "b/ADAPTIVE_P")
        nodes = s["frames"]["nodes"]
        fig, axes = plt.subplots(4, 4, figsize=(10, 10), layout="constrained")
        for i in range(4):
            text.append(
                f"| N{i} | {int(nodes[-1][i]['events'])} | {len({x.tobytes() for x in nodes['palette'][:, i]})} |"
            )
            for j, t in enumerate((0, 16, 24, 32)):
                axes[i, j].imshow(
                    nodes[round(t / 0.05)][i]["palette"].reshape(8, 8),
                    vmin=0,
                    vmax=4,
                    cmap="viridis",
                    interpolation="nearest",
                )
                axes[i, j].set(title=f"N{i}, t={t}", xticks=[], yticks=[])
        fig.savefig(figdir / "experiment_0012_morphology.png", dpi=150)
        plt.close(fig)
        text += [
            "",
            "Same opportunity times do not demonstrate asynchronous timing. Distinct palettes/patterns and any reversals are observable; event counts alone are not accumulated information or useful adaptation. Quiet/trace-off changes0, unforced OFF changes0, vetoes preserve structure. Own motion can still trigger source events when its fluid coupling is OFF.",
            "",
            "![Actual palettes through operation](figures/experiment_0012_morphology.png)",
            "",
        ]
        times = (16, 24, 32, 40)
        states = [io.snapshot(root / "b/ADAPTIVE_P" / f"{round(t / 0.05):06}.q12") for t in times]
        limit = max(float(np.max(abs(x["fields"][0, x["n"] // 2]))) for x in states)
        fig, axes = plt.subplots(1, 4, figsize=(13, 3.5), layout="constrained")
        for ax, t, state in zip(axes, times, states, strict=True):
            im = ax.imshow(
                state["fields"][0, state["n"] // 2],
                origin="lower",
                extent=(0, 24, 0, 24),
                cmap="RdBu_r",
                vmin=-limit,
                vmax=limit,
            )
            ax.scatter(state["positions"][:, 0], state["positions"][:, 1], s=10, c="black")
            ax.set(title=f"t={t}, z=12.25", xlabel="x", ylabel="y")
        fig.colorbar(im, ax=axes, label="signed pressure, common scale")
        fig.savefig(figdir / "experiment_0012_fluid.png", dpi=150)
        plt.close(fig)
        r = rows(root / "b/ADAPTIVE_P/metrics.csv")
        time = np.array([float(x["time"]) for x in r])

        def get(k):
            return np.array([float(x[k]) for x in r])

        fig, ax = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        ax[0].plot(time, get("fluid"), label="fluid")
        ax[0].plot(time, get("neural"), label="neurons")
        ax[0].plot(time, get("loss"), label="dissipated")
        ax[0].legend()
        ax[1].plot(time, get("fluid") + get("neural") + get("loss"), label="stored + dissipated")
        ax[1].plot(time, get("force_work") + get("switch_work"), "--", label="force + switch work")
        ax[1].legend()
        for aplot in ax:
            aplot.set(xlabel="normalized time", ylabel="actual energy/work")
        fig.savefig(figdir / "experiment_0012_energy.png", dpi=150)
        plt.close(fig)
        text += [
            "![Actual signed fluid plane, fixed scale](figures/experiment_0012_fluid.png)",
            "",
            "![Energy and externally actuated switch work](figures/experiment_0012_energy.png)",
            "",
        ]
    text += [
        "Original D NONADAPTIVE_P/F were actually ADAPTIVE because of a substring-selector defect. They are marked PROTOCOL_INVALID: 78 original intended conditions were validly executed, 2 were not. Two separately preregistered post-outcome diagnostics complete the missing control without replacing the original80 or revising their scientific gates. See [diagnostic registration](EXPERIMENT_0012_NONADAPTIVE_DIAGNOSTIC.md), actual metadata and separate ledgers. Total actual physical executions, including diagnostics: "
        + str(receipt["total_actual_trajectories"])
        + ".",
        "",
    ]
    text += ["## M2: exact-checkpoint causal branches", ""]
    if c:
        text += [
            "Full before-event state at16 is preserved byte-for-byte in each branch; the independent boundary verifier checks every unrelated private state, fluid field, port history and force account. Permit/veto changes only N0 palette and its explicit controller/work consequences. All subsequent opportunities are vetoed. No transient reset occurs.",
            "",
            "| Intervention vs veto | Node | Absolute delta norm | Grid error | Relative effect F | Onset | Verdict |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in c["effects"]:
            text.append(
                f"| {row['intervention']} | N{row['node']} | {row['norm']:.9g} | {row['grid_error']:.9g} | {row['relative_F']:.9g} | {row['onset']} | {row['verdict']} |"
            )
        text += [
            "",
            "Remote permit-veto signals are numerically resolved but below0.1% of their baseline responses: the registered remote gate FAILS. Detectable propagation is not sufficient potency. Isolated permit/veto remote u/v histories agree exactly on both grids, supporting the shared-fluid pathway. The sham matches total energy, not modal distribution; permit/sham differences therefore do not completely isolate coefficient changes from every state-perturbation explanation.",
            "",
        ]
        p = uv(root / "c/PERMIT_P") - uv(root / "c/VETO_P")
        f = uv(root / "c/PERMIT_F")[::2] - uv(root / "c/VETO_F")[::2]
        time = 16 + np.arange(len(p)) * 0.05
        fig, ax = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        for i in range(4):
            target = ax[0 if i == 0 else 1]
            target.plot(time, np.linalg.norm(p[:, i].reshape(len(p), -1), axis=1), label=f"N{i} P")
            target.plot(
                time, np.linalg.norm(f[:, i].reshape(len(f), -1), axis=1), "--", label=f"N{i} F"
            )
        for aplot in ax:
            aplot.set(xlabel="absolute normalized time", ylabel="norm of128 signed differences")
            aplot.legend(fontsize=8)
        ax[0].set_title("Own response")
        ax[1].set_title("Resolved remote effects below size threshold")
        fig.savefig(figdir / "experiment_0012_causal.png", dpi=150)
        plt.close(fig)
        text += [
            "![Actual permit-veto response differences](figures/experiment_0012_causal.png)",
            "",
        ]
    else:
        text += ["Causal branches NOT RUN; consult registered prerequisites.", ""]
    text += ["## M3: collective dynamics and controlled regimes", ""]
    if d:
        text += [
            "Actual all-node metrics, undefined phase-pair counts, spectra, work/dose and per-condition numerical values remain in collective-verification.json and collective-numerical.csv. Late statistics use the registered16..40 window, sampled at common.05 cadence on both grids; every underlying physical tick remains available. Undefined zero-response phases/diversity are not invented.",
            "",
            "| Seed | Morphological modulation | Increased diversity | Changes P/F |",
            "|---|---|---|---|",
        ]
        for x in d["standard_seeds"]:
            text.append(
                f"| {x['seed']} | {x['morphological_modulation']} | {x['increased_diversity']} | {x['changes']} |"
            )
        text += [
            "",
            "| Regime/perturbation | Relative effect | Delta / grid uncertainty | Verdict |",
            "|---|---|---|---|",
        ]
        for x in d["regimes"]:
            text.append(
                f"| {x['comparison']} | {x['relative_effect']:.9g} | {x['norm'] / max(x['grid_error'], 1e-30):.9g} | {x['verdict']} |"
            )
        text += [
            "",
            "COMMON drives all four bodies with amplitude.5. Four actual private-fluid INDi trajectories provide equivalent common forcing without reciprocal interaction. SOLO0 plus three explicitly analytic zero solutions supplies the single-source independent baseline; those zeros are not counted as runs. SIMPLE is a declared two-scalar-per-body control with identical two port geometries, not a substitute QR neuron or a fitted equal-spectrum model. Greater activity/diversity is not automatically better. Additional structural work can confound an increased-diversity/efficiency claim.",
            "",
        ]
        fig, ax = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
        labels = ("FIXED", "ADAPTIVE", "COMMON", "SIMPLE", "SUSTAINED_ADAPTIVE")
        for j, key in enumerate(("participation", "diversity", "PLV")):
            x = np.arange(len(labels))
            ax[j].bar(
                x - 0.18,
                [
                    d["observables"]["s409_" + label + "_P"][key]
                    if d["observables"]["s409_" + label + "_P"][key] is not None
                    else np.nan
                    for label in labels
                ],
                0.36,
                label="P",
            )
            ax[j].bar(
                x + 0.18,
                [
                    d["observables"]["s409_" + label + "_F"][key]
                    if d["observables"]["s409_" + label + "_F"][key] is not None
                    else np.nan
                    for label in labels
                ],
                0.36,
                label="F",
            )
            ax[j].set(title=key, xticks=x, xticklabels=labels)
            ax[j].tick_params(axis="x", rotation=45)
            ax[j].legend()
        fig.savefig(figdir / "experiment_0012_collective.png", dpi=150)
        plt.close(fig)
        fig, ax = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        for label in ("FIXED", "ADAPTIVE", "COMMON"):
            s = io.stream(root / "d" / ("s409_" + label + "_P"))
            v = s["frames"]["nodes"]["v"][320:, :, 9]
            freq = np.fft.rfftfreq(len(v), 0.05)
            ax[0].plot(freq, abs(np.fft.rfft(v[:, 1])) ** 2 / len(v) ** 2, label=label + " N1")
        ax[0].set(
            xlim=(0, 0.5), xlabel="cycles / normalized time", ylabel="signed-v spectral power"
        )
        ax[0].legend()
        control = d["controls"][0]
        bar = [
            control["private_common_observables"]["PLV"],
            control["shared_common_observables"]["PLV"],
        ]
        ax[1].bar(
            ["private fluids, common drive", "shared fluid, common drive"],
            [np.nan if x is None else x for x in bar],
        )
        ax[1].set(ylabel="mean phase locking", ylim=(0, 1))
        fig.savefig(figdir / "experiment_0012_spectra.png", dpi=150)
        plt.close(fig)
        text += [
            "![Registered collective observables](figures/experiment_0012_collective.png)",
            "",
            "![Signed spectra and common-drive control](figures/experiment_0012_spectra.png)",
            "",
        ]
    else:
        text += [
            "Collective matrix NOT RUN or pending; no collective potency verdict is inferred.",
            "",
        ]
    text += [
        "## M4: composition without a new physical law",
        "",
        "[Definitions and proof](EXPERIMENT_0012_COMPOSITION.md) specify typed complete-state partial maps and open node-pair interfaces. Identities/associative words are exact structural laws; they alone are potentially trivial. Shared fluid ownership and port order are explicit. No tensor product of closed private-fluid neurons is asserted.",
        "",
    ]
    if e:
        text += [
            f"Independent predictions were frozen before seed427 direct outcomes. Maximum full-field relative prediction error {max(x['field_error'] for x in e['comparisons']):.9g}; neural error{max(x['neural_error'] for x in e['comparisons']):.9g}. Full numerical refinement and all errors remain in composition-errors.csv and composition-verification.json. This demonstrates an independently implemented open-operator numerical model, not unique categorical predictive power over ordinary correct modular physics.",
            "",
            f"Formal verdicts: {formal['MATHEMATICAL_VALIDITY']}; physical agreement{e['PHYSICAL_AGREEMENT']}; predictive test{e['PREDICTIVE_UTILITY']}; categorical engineering advantage{formal['ENGINEERING_UTILITY']}. Both typed composition and the conventional physical validator reject the same6faults. The registered engineering-advantage test therefore FAILS. No invented code-saving, runtime or exclusivity advantage is claimed.",
            "",
        ]
        fig, ax = plt.subplots(figsize=(11, 4), layout="constrained")
        x = np.arange(len(e["comparisons"]))
        for key in ("field_error", "neural_error", "trace_error"):
            ax.semilogy(x, [v[key] for v in e["comparisons"]], ".-", label=key)
        ax.axhline(1e-10, color="black", ls="--", label="registered agreement bound")
        ax.set(xlabel="registered nonzero prediction checkpoint", ylabel="relative error")
        ax.legend()
        fig.savefig(figdir / "experiment_0012_composition.png", dpi=150)
        plt.close(fig)
        text += ["![Independent composition errors](figures/experiment_0012_composition.png)", ""]
    text += [
        "## Answers and limits",
        "",
        "M1: repeated in-operation local palette evolution is tested separately from numerical validity and consequence. M2: local structural response can produce a resolved remote signal through the fluid, yet the registered remote effect-size gate FAILS; signal detection is not sufficient potency. M3: the control/uncertainty tables above decide the actual finite driven collective results. M4: valid partial-map composition and independent physical prediction do not establish special categorical engineering advantage. No global success score.",
        "",
        "Only four genuine neurons were studied. There is no4096-body, mobile geometry, dissipative seawater, hardware QR material or biological learning result. Longer adaptive horizons, finer event-boundary stability, actuator/storage costs, larger populations and a fair speed/accuracy competition with established solvers remain missing. Historical QR10/QR11 and older failures stay frozen.",
        "",
        "## Delivery evidence",
        "",
        "Local format/lint/tests/build/docs, independent scientific decisions, archive integrity/fresh extraction, remote SHA and hosted CI are separate receipts. Inspect local-checks.json,archive-validation.json,delivery-status.json. Missing receipts mean pending actions, never scientific success. Large raw fields, ancestry, original verifier failures and all event ledgers remain outside Git.",
    ]
    Path("docs/EXPERIMENT_0012_RESULTS.md").write_text("\n".join(text) + "\n")
    csv_write(root / "VERDICTS.csv", [dict(question=k, verdict=v) for k, v in table])
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(json.dumps(document(a.root), indent=2))


if __name__ == "__main__":
    main()
