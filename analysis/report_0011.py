"""Measured QR11 figures, full execution coverage and viewer-independent report."""

# Long Markdown paragraphs are emitted as single report lines.
# ruff: noqa: E501
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis import io_0011 as io
from analysis.experiment_0009 import csv_write, rows
from analysis.plan_0011 import HELD, TRAIN

STAGES = {
    "l1": 13,
    "pilot": 35,
    "train": 32,
    "held": 64,
    "controls": 8,
    "retention_pilot": 26,
    "retention_train": 40,
    "retention_held": 80,
}


def expected(stage):
    if stage == "l1":
        return (
            [f"REF_{g}" for g in ("P", "T", "F")]
            + [f"{name}_{g}" for name in ("NEG", "QUIET", "OFF") for g in ("P", "F")]
            + ["SENSOR_OFF_P", "REPEAT_P", "ABPLUS_P", "ABMINUS_P"]
        )
    if stage == "pilot":
        names = [
            f"{prefix}{signal}_{g}"
            for signal in ("S9", "S27", "ORDER")
            for g in ("P", "T", "F")
            for prefix in ("cal_", "")
        ]
        names += [
            f"{prefix}{signal}_{g}"
            for signal in ("NEG", "SINGLE")
            for g in ("P", "F")
            for prefix in ("cal_", "")
        ]
        return (
            names
            + [
                f"{signal}_{g}"
                for signal in ("QUIET", "OFF", "TRACE_OFF", "SCRAMBLED")
                for g in ("P", "F")
            ]
            + ["REPEAT_P"]
        )
    if stage in ("train", "held"):
        seeds, grids = (TRAIN, ("P",)) if stage == "train" else (HELD, ("P", "F"))
        return [
            f"{prefix}s{s}_d{d}_m{m}_{g}"
            for s in seeds
            for d in (4, 6)
            for m in (9, 27)
            for g in grids
            for prefix in ("cal_", "")
        ]
    if stage == "controls":
        return [
            f"{prefix}{signal}_{g}"
            for signal in ("ORDER", "NEG")
            for g in ("P", "F")
            for prefix in ("cal_", "")
        ]
    if stage == "retention_pilot":
        return [
            f"{name}_{g}"
            for g in ("P", "F")
            for name in (
                "cal",
                "S9",
                "S27",
                "ORDER",
                "NEG",
                "SINGLE",
                "QUIET",
                "OFF",
                "TRACE_OFF",
                "SCRAMBLED",
                "FROZEN",
                "RESTORED_S9",
                "VIRGIN",
            )
        ]
    seeds, grids = (TRAIN, ("P",)) if stage == "retention_train" else (HELD, ("P", "F"))
    names = []
    for seed in seeds:
        for d in (4, 6):
            for g in grids:
                names.append(f"cal_s{seed}_d{d}_{g}")
                names.extend(
                    f"s{seed}_d{d}_h{h}_{variant}_{g}"
                    for h in (9, 27)
                    for variant in ("ADAPTED", "VIRGIN")
                )
    return names


def ledger(root):
    root = Path(root)
    records = []
    elapsed = 0
    raw = 0
    fluids = states = observations = 0
    reason = "Stage not executed; consult prerequisite receipts."
    for path in (
        "l1/gates.json",
        "pilot/gates.json",
        "morph_pilot/gates.json",
        "retention_pilot/gates.json",
    ):
        if (root / path).exists() and not json.loads((root / path).read_text()).get(
            "prerequisite_pass", False
        ):
            reason = "GATED by " + path
    for stage, count in STAGES.items():
        names = expected(stage)
        assert len(names) == count and len(set(names)) == count
        actual = (
            {r["case"]: r for r in rows(root / stage / "ledger.csv")}
            if (root / stage / "ledger.csv").exists()
            else {}
        )
        if (root / stage / "plan.csv").exists():
            assert {r["case"] for r in rows(root / stage / "plan.csv")} == set(names)
        assert set(actual) <= set(names)
        for name in names:
            entry = actual.get(name)
            status = entry["status"] if entry else "NOT RUN"
            duration = float(entry["elapsed_seconds"]) if entry else 0.0
            records.append(
                dict(
                    stage=stage,
                    case=name,
                    kind="PHYSICS",
                    status=status,
                    elapsed_seconds=duration,
                    reason="" if entry else reason,
                )
            )
            if entry:
                folder = root / stage / name
                elapsed += duration
                raw += sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
                fluids += len(list(folder.glob("*.q11")))
                states += len(list(folder.glob("*.n11")))
                observations += 1
    operations = []
    for stage in ("morph_pilot", "morph_main"):
        if (root / stage / "plan.csv").exists():
            for r in rows(root / stage / "plan.csv"):
                operations.append(
                    dict(
                        stage=stage,
                        case=r["case"],
                        kind="COMMIT_OPERATION",
                        status="COMPLETE"
                        if (root / stage / r["case"] / "after.n11").exists()
                        else "NOT RUN",
                        elapsed_seconds=0,
                        reason="Not a PDE integration",
                    )
                )
    csv_write(root / "EXECUTION_LEDGER.csv", records + operations)
    receipt = dict(
        schema=1,
        physical_executions=sum(r["status"] == "COMPLETE" for r in records),
        physical_not_run=sum(r["status"] == "NOT RUN" for r in records),
        preregistered_maximum=298,
        commit_operations=len(operations),
        physical_case_wall_seconds=elapsed,
        raw_case_bytes=raw,
        full_fluid_fields=fluids,
        full_neuron_checkpoints=states,
        every_tick_observation_streams=observations,
        stop_reason=reason if any(r["status"] == "NOT RUN" for r in records) else None,
    )
    assert elapsed <= 3600 and raw <= 16_000_000_000
    (root / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def document(root):
    root = Path(root)
    receipt = ledger(root)
    figdir = Path("docs/figures")
    figdir.mkdir(exist_ok=True)
    l1 = json.loads((root / "l1/gates.json").read_text())
    pilot = (
        json.loads((root / "pilot/gates.json").read_text())
        if (root / "pilot/gates.json").exists()
        else None
    )
    text = [
        "# Experiment 0011: the listening QR neuron\n",
        "Registration `3ba0680` precedes implementation `bc599b9` and all new outcomes. Earlier experiments remain unchanged; QR10's nine held-out source decoders remain FAIL. Principle 002 is a proposed mechanism, not an experimentally established law. No overall success score.\n",
        "## Separate scientific verdicts\n",
        "| Capability | Verdict | Evidence |",
        "|---|---|---|",
    ]
    for name, value in l1["L1"].items():
        text.append(f"| L1 {name} | {value} | l1/scientific-gates.csv |")
    if pilot:
        for key in ("L2_mechanistic", "L2_structure", "L3_equal_work"):
            text.append(f"| {key} | {pilot[key]} | pilot/gates.json |")
    communication = (
        json.loads((root / "communication-verification.json").read_text())
        if (root / "communication-verification.json").exists()
        else None
    )
    if communication:
        for model in communication["L2_L3_models"]:
            if model["primary"]:
                text.append(
                    f"| L3 held-out SIGNED, d{model['distance']}m | {model['verdict']} | models.csv; predictions.csv |"
                )
    morph = (
        json.loads((root / "morph_pilot/gates.json").read_text())
        if (root / "morph_pilot/gates.json").exists()
        else None
    )
    retention = (
        json.loads((root / "retention_pilot/gates.json").read_text())
        if (root / "retention_pilot/gates.json").exists()
        else None
    )
    final_retention = (
        json.loads((root / "retention-verification.json").read_text())
        if (root / "retention-verification.json").exists()
        else None
    )
    text.append(
        f"| L4 receiver morphology pilot | {morph['L4'] if morph else 'INDETERMINATE (NOT RUN)'} | morph_pilot/gates.json |"
    )
    text.append(
        f"| L5 post-reset causal response pilot | {retention['L5_causal'] if retention else 'INDETERMINATE (NOT RUN)'} | retention_pilot/gates.json |"
    )
    if final_retention:
        for row in final_retention["L5_improvement"]:
            text.append(
                f"| L5 held-out improvement, d{row['distance']}m | {row['verdict']} | retention_improvement.csv |"
            )
    else:
        text.append(
            "| L5 held-out retained-information improvement | INDETERMINATE (NOT RUN) | Dependent stage gates |"
        )
    text += [
        "\n## Actual execution and local state\n",
        f"{receipt['physical_executions']} actual physical trajectories; {receipt['physical_not_run']} registered trajectories NOT RUN; {receipt['commit_operations']} separately counted commitment operations. {receipt['full_fluid_fields']} full signed fluid checkpoints, {receipt['full_neuron_checkpoints']} complete owned-state checkpoints, and {receipt['every_tick_observation_streams']} every-tick state/trace streams. Case wall time {receipt['physical_case_wall_seconds']:.6f}s; raw case bytes {receipt['raw_case_bytes']}. Ceilings:3600s and16GB. Full ledger contains every one of the298 possible physical conditions and the actual stopping reason.\n",
        "Two stationary QR neurons in main experiments; three in the L1 dual-source reference controls. Every instantiated neuron has the same local sensor/trace/morphology implementation, independently owned 8x8 palette,64u/v pairs and405 bounded trace components. Source/receiver designations belong to the apparatus. The neuron receives only its own finite-support local packet, current own state and dt; no source identity, seed, label, prediction, future sample or global-field API.\n",
        "The adapter preserves QR10 physics. QR6/QR7 full-lattice morphology/reset APIs are incompatible with its isolated state; the new adapter implements explicit local coefficient rebuilding, switch work and reset boundaries. Unit tests cover passive-physics invariance, owned-state reset/serialization, source-work-only calibration and source-excluded readouts. Scientific audits are separate from software tests.\n",
    ]
    # Real local waveforms and owned traces, same fixed channels/times across conditions.
    if (root / "pilot/S9_P/observations.q11o").exists():
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        streams = {
            name: io.stream(root / "pilot" / name / "observations.q11o")
            for name in ("S9_P", "ORDER_P", "NEG_P")
        }
        for name, s in streams.items():
            t = np.arange(s["ticks"] + 1) * s["dt"]
            axes[0].plot(t, s["frames"]["nodes"][:, 1]["packet"][:, 0], label=name)
        s = streams["S9_P"]
        t = np.arange(s["ticks"] + 1) * s["dt"]
        z = s["frames"]["nodes"][:, 1]["z"].reshape(len(t), 3, 135)
        for i, tau in enumerate((0.5, 2, 8)):
            axes[1].plot(t, z[:, i, 0], label=f"tau={tau}")
        axes[0].set(
            xlabel="normalized time",
            ylabel="actual local signed pressure q",
            title="Local receiver sensor, equal external work",
        )
        axes[1].set(
            xlabel="normalized time",
            ylabel="bounded owned signed-pressure trace",
            title="Online causal multi-timescale state",
        )
        for ax in axes:
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
        fig.savefig(figdir / "experiment_0011_sensing_traces.png", dpi=160)
        plt.close(fig)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        for name in ("S9_P", "NEG_P", "ORDER_P"):
            s = streams[name]
            t = np.arange(s["ticks"] + 1) * s["dt"]
            z = s["frames"]["nodes"][:, 1]["z"].reshape(len(t), 3, 135)
            axes[0].plot(t, z[:, 2, 0], label=name)
            axes[1].plot(t, z[:, 2, 4], label=name)
        axes[0].set(
            xlabel="normalized time",
            ylabel="tau8 signed pressure trace",
            title="Wave polarity retained",
        )
        axes[1].set(
            xlabel="normalized time",
            ylabel="tau8 energy-density trace",
            title="Complete sign inversion leaves energy unchanged",
        )
        for ax in axes:
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
        fig.savefig(figdir / "experiment_0011_sign_energy.png", dpi=160)
        plt.close(fig)
        text += [
            "![Actual local sensors and online traces](figures/experiment_0011_sensing_traces.png)\n",
            "![Signed versus energy-only trace control](figures/experiment_0011_sign_energy.png)\n",
        ]
    text += [
        "## Energy matching and numerical validity\n",
        "Every active exposure has a separate frozen-morphology, unit-amplitude physical calibration. Rust reads only SOURCE external net work, sets amplitude=sqrt(1/Wunit), and executes a fresh trajectory. Calibration receiver histories never fit a decoder. Actual net work must equal1 within1e-10; positive/negative source work, fluid emission/backflow and receiver energy remain separate. Equal supplied work is not equal emitted or received energy. OFF controls reuse a declared amplitude and are not asserted work-matched.\n",
        "Three12-unit pulses begin0,16,32; source modules9/27; MID carrier. Standard signs[+,+,-], ORDER[-,+,+], NEG[-,-,+], SINGLE only the last negative pulse. ORDER has the same unscaled absolute envelope; independent work calibration can change overall gain. SINGLE changes recent amplitude after matching total work. Neither comparison by itself isolates every possible local-magnitude explanation.\n",
        "Causal trace law z_next=exp(-dt/tau)*z+(1-exp(-dt/tau))*phi, tau(.5,2,8). Phi is explicitly bounded; the physical state is not clipped or normalized.405 components are fixed capacity, not an unlimited history buffer. Sampling is read-only after the complete physical split. Independent Python reconstructs all405 updates at every actual tick, exact kicks/exchange, every local neural ODE step and damping loss, plus full-checkpoint fluid energy/local sensors. This is not a second complete fluid PDE integration.\n",
    ]
    numerical = []
    for stage in ("l1", "pilot"):
        path = root / stage / "scientific-gates.csv"
        if path.exists():
            for row in rows(path):
                if row.get("category") == "refinement" or row.get("question") == "validity":
                    numerical.append(
                        (stage + " " + row.get("case", "") + " " + row["gate"], float(row["value"]))
                    )
    if numerical:
        fig, ax = plt.subplots(figsize=(11, 4), layout="constrained")
        ax.plot(np.arange(len(numerical)), [x[1] for x in numerical], "o", ms=3)
        ax.axhline(0.1, color="black", ls="--", label="registered10% limit")
        ax.set(
            xlabel="all registered L1/pilot comparison index",
            ylabel="relative whole-field/packet/trace disagreement",
            title="Unaligned temporal/spatial refinement, no trajectory correction",
        )
        ax.legend()
        fig.savefig(figdir / "experiment_0011_numerical.png", dpi=160)
        plt.close(fig)
        text.append("![Registered numerical comparisons](figures/experiment_0011_numerical.png)\n")
    # All equal-work pilot inputs, including the independent calibration gains.
    target = []
    if (root / "pilot/plan.csv").exists():
        for row in rows(root / "pilot/plan.csv"):
            if (
                row["policy"].startswith("work1:")
                and (root / "pilot" / row["case"] / "COMPLETE").exists()
            ):
                m = rows(root / "pilot" / row["case"] / "metadata.csv")[0]
                last = rows(root / "pilot" / row["case"] / "metrics.csv")[-1]
                target.append(
                    dict(
                        case=row["case"],
                        amplitude=float(m["amplitude"]),
                        net_work=float(last["work"]),
                        positive_work=float(last["positive_work"]),
                        negative_work=float(last["negative_work"]),
                        emitted_positive=float(last["source_positive"]),
                        backflow=float(last["source_backflow"]),
                    )
                )
    if target:
        csv_write(root / "matched_work_summary.csv", target)
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        x = np.arange(len(target))
        axes[0].plot(x, [r["net_work"] for r in target], "o", label="net work")
        axes[0].plot(x, [r["positive_work"] for r in target], "s", label="positive supplied work")
        axes[0].plot(x, [r["negative_work"] for r in target], "^", label="returned source work")
        axes[1].plot(
            x, [r["emitted_positive"] for r in target], "o", label="positive fluid emission"
        )
        axes[1].plot(x, [r["backflow"] for r in target], "s", label="source backflow")
        for ax in axes:
            ax.set(
                xlabel="all active pilot condition index", ylabel="actual work (model energy units)"
            )
            ax.legend(fontsize=7)
            ax.grid(alpha=0.3)
        fig.savefig(figdir / "experiment_0011_work.png", dpi=160)
        plt.close(fig)
        text.append(
            "![Actual supplied work, emission and backflow](figures/experiment_0011_work.png)\n"
        )
    text += [
        "## Held-out temporary representations\n",
        "Four training seeds307,311,313,317; four held-out331,337,347,349. Pilot301 and reference211 never fit templates. Ten models were frozen before held execution: five registered representations at each of4m/6m. SIGNED18 is primary; ENERGY3, ALL_TRACE405, INSTANT128 and QR10_STYLE12928 are separate secondary instruments. No best-model replacement, feature tuning, seed substitution, phase alignment or label feedback. Different dimensional budgets are explicit.\n",
    ]
    if communication:
        modelrows = communication["L2_L3_models"]
        text += [
            "| Distance | Representation | Dimension | Primary correct/8 | Fine correct/8 | Stable | Max feature error | Min separation/grid error | Verdict |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in modelrows:
            text.append(
                f"| {r['distance']}m | {r['representation']} | {r['dimension']} | {r['correct_P']} | {r['correct_F']} | {r['stable']} | {r['max_feature_refinement']:.8g} | {r['min_separation_to_uncertainty']:.8g} | {r['verdict']} |"
            )
        p = rows(root / "predictions.csv")
        text.append(
            f"\nAll{len(p)} training/held/grid predictions retained, including{sum(r['correct'] == 'False' for r in p)} incorrect and{sum(r['tie'] == 'True' for r in p)} ties. Variability.csv separates within-seed source differences from between-seed deviations from training means. These are external scientific readouts, never autonomous neuron recognition.\n"
        )
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        for ax, d in zip(axes, (4, 6), strict=True):
            selected = [r for r in modelrows if r["distance"] == d]
            x = np.arange(len(selected))
            ax.bar(x - 0.18, [r["correct_P"] for r in selected], 0.36, label="primary")
            ax.bar(x + 0.18, [r["correct_F"] for r in selected], 0.36, label="fine")
            ax.axhline(7, color="black", ls="--", lw=1)
            ax.set(
                xticks=x,
                xticklabels=[r["representation"] for r in selected],
                ylim=(0, 9.5),
                ylabel="correct out of8 held cases",
                title=f"{d}m: correctness does not replace numerical gates",
            )
            ax.tick_params(axis="x", labelrotation=35)
            for i, r in enumerate(selected):
                ax.text(i, 8.7, r["verdict"], ha="center", fontsize=7)
            ax.legend(fontsize=7)
        fig.savefig(figdir / "experiment_0011_decoding.png", dpi=160)
        plt.close(fig)
        text.append(
            "![All frozen readouts and full verdicts](figures/experiment_0011_decoding.png)\n"
        )
    else:
        text.append("Held-out readout NOT RUN or incomplete; no recognition claim.\n")
    text += [
        "## Actual morphology and retention\n",
        "The candidate swaps up to four disjoint eligible unequal-color cardinal pairs using only own H/C trace scores. There is no minimum edit count, label, target shape or receiver-only rule. All pre/post arrays, module scores, accepted swaps, independently reconstructed eligibility/ranks, legal colors/histograms and actual Epost-Epre switching work are retained. Switching is externally actuated; reset later removes recorded physical energy. Palette changes alone do not establish useful memory.\n",
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.7), layout="constrained")
    if morph:
        before = io.neurons(root / "morph_pilot/S9_P/before.n11")["nodes"][1]["palette"]
        p = io.neurons(root / "morph_pilot/S9_P/after.n11")["nodes"][1]["palette"]
        f = io.neurons(root / "morph_pilot/S9_F/after.n11")["nodes"][1]["palette"]
        for ax, a, title in zip(
            axes,
            (before, p, f),
            ("actual original receiver", "actual committed primary", "actual committed fine"),
            strict=True,
        ):
            ax.imshow(a.reshape(8, 8), vmin=0, vmax=4, cmap="viridis", interpolation="nearest")
            ax.set(title=title, xticks=range(8), yticks=range(8))
        text += [
            "| Morphology pilot condition | Source edits | Receiver edits | Receiver switch work |",
            "|---|---|---|---|",
        ]
        for name, result in morph["all_nodes"].items():
            text.append(
                f"| {name} | {result['nodes'][0]['edits']} | {result['nodes'][1]['edits']} | {result['nodes'][1]['switch_work']:.9g} |"
            )
        text.append(
            f"\nL4 pilot verdict **{morph['L4']}**. Full failed numerical/structural gates remain in morph_pilot/gates.csv. Receiver edit consistency gates retention; source edits/refinement are independently reported and source morphology is restored before every causal receiver probe.\n"
        )
        text += [
            "| Condition | Node | Edited-position P/F Jaccard | Exact palette agreement |",
            "|---|---|---|---|",
        ]
        for row in morph.get("numerical_morphology", []):
            text.append(
                f"| {row['condition']} | {row['neuron']} | {row['jaccard']:.9g} | {row['palette_equal']} |"
            )
        text += [
            "\n| Primary receiver history | Palette positions different from S9 |",
            "|---|---|",
        ]
        for label in ("S27", "ORDER", "NEG", "SINGLE", "SCRAMBLED"):
            other = io.neurons(root / "morph_pilot" / (label + "_P") / "after.n11")["nodes"][1][
                "palette"
            ]
            text.append(f"| {label} | {np.count_nonzero(other != p)} |")
        if (root / "morph_main/verification.json").exists():
            text += [
                "\n| Held seed | Distance | History module | Node | P/F palette differences | Edited-position Jaccard |",
                "|---|---|---|---|---|---|",
            ]
            for seed in HELD:
                for distance in (4, 6):
                    for module in (9, 27):
                        operations = [
                            root / "morph_main" / f"s{seed}_d{distance}_m{module}_{grid}"
                            for grid in ("P", "F")
                        ]
                        palettes = [
                            io.neurons(path / "after.n11")["nodes"]["palette"]
                            for path in operations
                        ]
                        originals = [
                            io.neurons(path / "before.n11")["nodes"]["palette"]
                            for path in operations
                        ]
                        for node in (0, 1):
                            edits = [
                                set(np.flatnonzero(a[node] != b[node]))
                                for a, b in zip(palettes, originals, strict=True)
                            ]
                            union = edits[0] | edits[1]
                            jaccard = len(edits[0] & edits[1]) / len(union) if union else 1.0
                            different = np.count_nonzero(palettes[0][node] != palettes[1][node])
                            text.append(
                                f"| {seed} | {distance}m | {module} | {node} | {different} | {jaccard:.9g} |"
                            )
    else:
        for ax in axes:
            ax.axis("off")
            ax.text(0.5, 0.5, "Morphology NOT RUN\nprerequisite gate", ha="center", va="center")
    fig.savefig(figdir / "experiment_0011_morphology.png", dpi=160)
    plt.close(fig)
    text.append(
        "![Actual palettes or explicitly unexecuted stage](figures/experiment_0011_morphology.png)\n"
    )
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    if retention:
        for label in ("S9", "S27", "VIRGIN", "RESTORED_S9", "SCRAMBLED"):
            s = io.stream(root / "retention_pilot" / (label + "_P") / "observations.q11o")
            ax.plot(
                np.arange(s["ticks"] + 1) * s["dt"],
                s["frames"]["nodes"][:, 1]["u"][:, 9],
                label=label,
            )
        ax.set(
            xlabel="normalized probe time",
            ylabel="actual receiver module9 signed u",
            title="Same probe after exact transient/trace reset",
        )
        ax.legend(fontsize=8)
        text.append(
            f"L5 causal pilot **{retention['L5_causal']}**. Initial full fields/owned snapshots prove zero u/v,fluid,packets,previous pressure,405 traces,age,commit flags and work/loss/port accounts. Source palette is restored; only declared receiver palette persists. VIRGIN is a fresh body. RESTORED_S9 restores receiver palette at zero state. Probe waveform/amplitude identical across retained histories; actual work variation is separately gated1%. See reset.csv and retention_pilot/gates.csv.\n"
        )
        text += [
            "| Retained history | Grid | Full response difference / virgin norm | Absolute difference norm | Source work difference / virgin work |",
            "|---|---|---|---|---|",
        ]
        for grid in ("P", "F"):
            base = root / "retention_pilot" / ("VIRGIN_" + grid)
            virgin = io.stream(base / "observations.q11o")["frames"]["nodes"][:, 1]
            original = np.stack((virgin["u"], virgin["v"]), axis=-1).ravel()
            work = float(rows(base / "metrics.csv")[-1]["work"])
            for label in (
                "S9",
                "S27",
                "ORDER",
                "NEG",
                "SINGLE",
                "QUIET",
                "OFF",
                "TRACE_OFF",
                "SCRAMBLED",
                "FROZEN",
                "RESTORED_S9",
            ):
                folder = root / "retention_pilot" / (label + "_" + grid)
                node = io.stream(folder / "observations.q11o")["frames"]["nodes"][:, 1]
                value = np.stack((node["u"], node["v"]), axis=-1).ravel()
                delta = float(np.linalg.norm(value - original))
                change = abs(float(rows(folder / "metrics.csv")[-1]["work"]) - work) / abs(work)
                text.append(
                    f"| {label} | {grid} | {delta / max(float(np.linalg.norm(original)), 1e-30):.9g} | {delta:.9g} | {change:.9g} |"
                )
    else:
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "Retention NOT RUN\nDependent morphology gate not met",
            ha="center",
            va="center",
            fontsize=14,
        )
        text.append(
            "L5 retention is **NOT RUN**, not a negative response result. Its mandatory prerequisite gate was not met.\n"
        )
    fig.savefig(figdir / "experiment_0011_retention.png", dpi=160)
    plt.close(fig)
    text.append(
        "![Post-reset response or explicitly unexecuted stage](figures/experiment_0011_retention.png)\n"
    )
    if final_retention:
        text += [
            "| Distance | Variant | Primary correct/8 | Fine correct/8 | Ties | Verdict |",
            "|---|---|---|---|---|---|",
        ]
        for r in final_retention["L5_models"]:
            text.append(
                f"| {r['distance']}m | {r['variant']} | {r['correct_P']} | {r['correct_F']} | {r['ties']} | {r['verdict']} |"
            )
        text.append(
            "All retention predictions, uncertainties and adapted/virgin contrasts remain in retention_*.csv. Improvement requires a valid adapted pass and higher held correctness on BOTH grids, not a bigger response.\n"
        )
    text += [
        "## Answers to the eight scientific questions\n",
        f"1. **Local sensing:** L1 component verdicts {l1['L1']}. Every instantiated node has identical sensing code, and all measured local fields are checked against its own transducer support.\n",
        f"2. **Causal internal history:** {pilot['L2_mechanistic'] if pilot else 'NOT RUN'}. Independent reconstruction checks every405-component online update from current local samples and own mechanical state, without future/history-file access. Evidence: observations.q11o,audit.json.\n",
        f"3. **Distinguishable structure:** pilot {pilot['L2_structure'] if pilot else 'NOT RUN'} for matched-work reordered input and polarity controls. Cross-seed identity results remain the separate frozen-model table; within-seed separation is not generalization. Evidence: pilot/gates.json,predictions.csv,variability.csv.\n",
        f"4. **Persistent morphology:** {morph['L4'] if morph else 'NOT RUN'} under the local trace law and numerical edit-consistency gate. Actual changes, zeros, legality and external switch work are individually recorded; changes alone are not useful memory.\n",
        f"5. **Post-reset causal behavior:** {retention['L5_causal'] if retention else 'NOT RUN (gated)'}. Only this stage can establish changed response carried by persistent morphology after temporary state removal.\n",
        "6. **Experience versus alternatives:** paired same-seed virgin/frozen/trace-off/quiet/restored controls address initialization and hidden transients where executed. Equal net work addresses supplied dose; it does not equalize emitted/local absorbed energy. Signed polarity tests separate information from even energy, but the morphology rule is itself polarity-even. Local-magnitude explanations and necessity of repetition are not automatically excluded. No stronger conclusion is inferred from structural change.\n",
        f"7. **Held-out usefulness:** {'See retained-response and improvement verdicts above.' if final_retention else 'NOT RUN: dependent retention/discrimination matrix gated.'} Temporary trace decoding alone cannot answer this. External templates are measuring apparatus, never neuron memory.\n",
        "8. **Scaling limits:** no4096-neuron dynamics were executed. Owned trace storage would be13,271,040bytes for4096 nodes (arithmetic estimate, not measured scaling). At N96 each radius1.5m kernel has up to1728 cells; two reciprocal ports plus local sensing per node add substantial sampling/split work and overlapping-kernel interactions requiring new numerical validation. Every-tick full owned-state scientific recording would grow to roughly35GB per48-unit fine trajectory. Performance, collective validity, useful retention, energy costs and autonomous repeated commitment remain unresolved.\n",
        "## Verification and delivery boundaries\n",
        "Full fields/owned states/trace streams, calibration and source-work associations, reset/commit receipts, all wrong/tied/invalid predictions, complete298-condition ledger, source/compiler/executable provenance and integrity manifests remain outside Git. Small measured figures/report/source are versioned. Original QR10/QR7 failures stay intact. Local strict software checks, independent scientific audits, archive verification, pushed SHA and hosted CI are separate receipts. No viewer, GPU physics, native-window or FPS claim.\n",
    ]
    Path("docs/EXPERIMENT_0011_RESULTS.md").write_text("\n".join(text).rstrip() + "\n")
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(json.dumps(document(a.root), indent=2))


if __name__ == "__main__":
    main()
