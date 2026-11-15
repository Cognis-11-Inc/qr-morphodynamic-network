"""Export measured QR8 verdicts, complete tables and fixed-scale scientific plots."""

# ruff: noqa: E501 -- Generated scientific Markdown paragraphs and table rows.
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from analysis import experiment_0008 as q
from analysis.experiment_0005 import rows


def table(path, records):
    if not records:
        path.write_text("no records\n")
        return
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def export(root, result):
    folder = root / "tables"
    folder.mkdir(exist_ok=True)
    for name in (
        "predictions",
        "propagation",
        "spreading",
        "arrivals",
        "symmetry",
        "superposition",
    ):
        table(folder / (name + ".csv"), result[name])
    table(folder / "refinement.csv", list(result["refinement"].values()))
    records = []
    margins = []
    for model in result["decoders"]:
        counts = model["counts"]
        records.append(
            dict(
                pair=model["pair"],
                key=model["key"],
                dimension=model["dimension"],
                train_correct=counts["train"]["correct"],
                held_correct=counts["evaluate"]["correct"],
                fine_correct=counts["refine"]["correct"],
                held_ties=counts["evaluate"]["ties"],
                fine_ties=counts["refine"]["ties"],
                field_valid=model["field_valid"],
                consistent=model["predictions_consistent"],
                verdict=model["verdict"],
            )
        )
        margins.extend(dict(pair=model["pair"], key=model["key"], **m) for m in model["margins"])
    table(folder / "decoders.csv", records)
    table(folder / "margins.csv", margins)
    ledgers = []
    for stage in ("train", "evaluate", "refine", "repeat"):
        ledgers.extend(dict(stage=stage, **r) for r in rows(root / stage / "ledger.csv"))
    table(folder / "execution_ledger.csv", ledgers)
    initial = []
    spatial = []
    for stage in ("train", "evaluate", "refine", "repeat"):
        for case in sorted((root / stage).iterdir()):
            if not case.is_dir() or not (case / "COMPLETE").exists():
                continue
            params = rows(case / "parameters.csv")[0]
            row = rows(case / "metrics.csv")[0]
            initial.append(
                dict(
                    stage=stage,
                    id=case.name,
                    signal=params["signal"],
                    participation=float(row["participation"]),
                    active_receivers=float(row["active_receivers"]),
                    other_energy=float(row["other_energy"]),
                    other_motion=float(row["other_motion"]),
                    cross_energy=float(row["cross_energy"]),
                    cross_motion=float(row["cross_motion"]),
                )
            )
            target = root / "spatial" / stage / case.name
            target.mkdir(parents=True, exist_ok=True)
            for time in (0, *q.TIMES):
                frame = q.checkpoint(root, stage, int(params["seed"]), params["signal"], time)
                omega2 = q.coefficients(frame["palette"])[0]
                energy = (frame["k"] + frame["q"]).sum(axis=(1, 2))
                motion = (frame["k"] + 0.5 * omega2 * frame["u"] ** 2).sum(axis=(1, 2))
                array = np.stack((energy, motion), axis=-1).astype("<f8")
                name = f"{frame['tick']:06}.f64"
                array.tofile(target / name)
                spatial.append(
                    dict(
                        stage=stage,
                        id=case.name,
                        time=time,
                        tick=frame["tick"],
                        path=str((target / name).relative_to(root)),
                        neurons=4096,
                        components="mechanical,motion",
                    )
                )
    p2 = []
    for stage in ("evaluate", "refine"):
        for seed in q.HELD:
            for signal in q.SIGNALS[:6]:
                data = rows(root / stage / f"s{seed}_{signal}" / "metrics.csv")
                dt = 0.025 if stage == "evaluate" else 0.0125
                for time in q.TIMES:
                    row = data[round(time / dt)]
                    energy = sum(float(row[k]) for k in ("kinetic", "onsite", "coupling"))
                    fraction = float(row["other_motion"]) / energy
                    p2.append(
                        dict(
                            stage=stage,
                            seed=seed,
                            signal=signal,
                            time=time,
                            participation=float(row["participation"]),
                            active_receivers=float(row["active_receivers"]),
                            other_motion_fraction=fraction,
                            participation_gate=float(row["participation"]) >= 8,
                            receiver_gate=float(row["active_receivers"]) >= 8,
                            cross_motion_gate=fraction >= 0.01,
                        )
                    )
    table(folder / "P2_components.csv", p2)
    table(folder / "initial_distribution.csv", initial)
    table(folder / "spatial_index.csv", spatial)


def model(result, pair, key):
    return next(m for m in result["decoders"] if m["pair"] == pair and m["key"] == key)


def plots(root, result, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm, SymLogNorm

    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "figure.dpi": 150})
    seed = 127
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for signal in ("S9p", "S9m", "S27p", "S27m"):
        data = rows(root / "evaluate" / f"s{seed}_{signal}" / "metrics.csv")
        axes[0].plot(
            [float(r["time"]) for r in data],
            [sum(float(r[k]) for k in ("kinetic", "onsite", "coupling")) for r in data],
            "--" if signal.endswith("m") else "-",
            label=signal,
        )
    for signal in ("ABp", "ABm"):
        data = rows(root / "evaluate" / f"s{seed}_{signal}" / "metrics.csv")
        axes[1].plot(
            [float(r["time"]) for r in data],
            [sum(float(r[k]) for k in ("kinetic", "onsite", "coupling")) for r in data],
            label=signal,
        )
    for ax in axes[:2]:
        ax.set(xlabel="physical time", ylabel="total mechanical energy", ylim=(0, 1.05))
        ax.legend()
    axes[0].set_title("seed127: sign inversion preserves quadratic energy")
    axes[1].set_title("equal E0=1; global dual-source energy")
    fig.savefig(out / "experiment_0008_global_energy.png")
    plt.close(fig)
    from analysis.audit_experiment_0008 import module_streams

    fig, axes = plt.subplots(1, 3, figsize=(15, 4), constrained_layout=True)
    folder = root / "evaluate/s127_S9p"
    stream = module_streams(folder)[0]
    t = np.array(stream["tick"]) * 0.025
    for i, d in enumerate(q.DISTANCES):
        axes[0].plot(t, stream["values"][:, i, 3], label=f"distance{d}")
        axes[1].plot(t, stream["values"][:, i, 2], label=f"distance{d}")
    axes[0].set(
        yscale="log",
        ylim=(1e-12, 1),
        xlabel="physical time",
        ylabel="receiver kinetic + onsite energy",
        title="A-shell actual motion; excludes half-edge allocation",
    )
    axes[0].axhline(1e-8, color="black", ls="--", label="registered arrival threshold")
    axes[1].set(
        xlabel="physical time",
        ylabel="receiver mechanical energy / retained E",
        title="Retained-energy fractions; absolute energy shown at left",
        ylim=(0, 1),
    )
    for ax in axes[:2]:
        ax.legend(fontsize=7)
    for signal in ("S9p", "S27p", "ABp", "ABm"):
        data = rows(root / "evaluate" / f"s127_{signal}" / "metrics.csv")
        axes[2].plot(
            [float(r["time"]) for r in data],
            [float(r["participation"]) for r in data],
            label=signal,
        )
    axes[2].axhline(8, color="black", ls="--", label="registered P2 requirement")
    axes[2].set(
        xlabel="physical time",
        ylabel="effective energy participation (neurons)",
        ylim=(0, 10),
        title="Many weak responses; energy remains concentrated",
    )
    axes[2].legend(fontsize=7)
    fig.savefig(out / "experiment_0008_propagation.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(10, 6), constrained_layout=True)
    for ri, signal in enumerate(("S9p", "S27p")):
        for col, t in enumerate((0, 8, 32)):
            frame = q.checkpoint(root, "evaluate", seed, signal, t)
            energy = (frame["k"] + frame["q"]).sum(axis=(1, 2)).reshape(16, 16, 16).sum(axis=0)
            image = axes[ri, col].imshow(
                np.ma.masked_less(energy, 1e-10),
                origin="lower",
                norm=LogNorm(1e-10, 1),
                cmap="magma",
            )
            axes[ri, col].set(title=f"{signal}, t={t}; sum over z", xlabel="x", ylabel="y")
    fig.colorbar(image, ax=axes, label="actual mechanical energy; fixed 1e-10 to E0=1", shrink=0.8)
    fig.savefig(out / "experiment_0008_spatial_energy.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), constrained_layout=True)
    for ri, signal in enumerate(("ABp", "ABm")):
        frame = q.checkpoint(root, "evaluate", seed, signal, 16)
        for col, field in enumerate(("u", "v")):
            data = frame[field].reshape(16, 16, 16, 64)[8, :, :, 27]
            im = axes[ri, col].imshow(
                data,
                origin="lower",
                cmap="coolwarm",
                norm=SymLogNorm(linthresh=1e-6, vmin=-1.8, vmax=1.8),
            )
            axes[ri, col].set(title=f"{signal} {field}27, z8, t16", xlabel="x", ylabel="y")
        energy = (frame["k"] + frame["q"]).sum(axis=(1, 2)).reshape(16, 16, 16).sum(axis=0)
        en = axes[ri, 2].imshow(
            np.ma.masked_less(energy, 1e-10), origin="lower", norm=LogNorm(1e-10, 1), cmap="magma"
        )
        axes[ri, 2].set(title=f"{signal} energy, sum over z", xlabel="x", ylabel="y")
    fig.colorbar(
        im, ax=axes[:, :2], label="signed field; shared symlog scale (linear below1e-6)", shrink=0.7
    )
    fig.colorbar(en, ax=axes[:, 2], label="mechanical energy; fixed scale", shrink=0.7)
    fig.savefig(out / "experiment_0008_interference.png")
    plt.close(fig)
    for mask in ("all", "cross"):
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
        for ax, pair in zip(axes.ravel(), q.PAIRS, strict=True):
            family = "F" if pair == "DUAL" else "A"
            reps = ("SH", "T", "U", "KP", "UV")
            values = np.array(
                [
                    [
                        model(result, pair, f"{family}{d}_{mask}_{rep}")["counts"]["evaluate"][
                            "correct"
                        ]
                        for d in q.DISTANCES
                    ]
                    for rep in reps
                ]
            )
            im = ax.imshow(values, vmin=0, vmax=8, cmap="viridis", aspect="auto")
            for i, rep in enumerate(reps):
                for j, d in enumerate(q.DISTANCES):
                    item = model(result, pair, f"{family}{d}_{mask}_{rep}")
                    ax.text(
                        j,
                        i,
                        f"{values[i, j]}/8\n{item['verdict'][0]}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if values[i, j] < 5 else "black",
                    )
            ax.set(
                title=f"{pair}: {family} regions, {mask}",
                xticks=range(5),
                xticklabels=q.DISTANCES,
                yticks=range(5),
                yticklabels=reps,
                xlabel="distance (no near/far pooling)",
            )
        fig.colorbar(
            im, ax=axes, label="held-out correct / 8; P/F/I denotes gated verdict", shrink=0.8
        )
        fig.savefig(out / f"experiment_0008_readout_{mask}.png")
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    cases = list(result["refinement"].values())
    values = [100 * r["maximum_error"] for r in cases]
    axes[0].bar(
        range(len(values)), values, color=["#b33939" if v > 1.5 else "#287b9c" for v in values]
    )
    axes[0].axhline(1.5, ls="--", color="black", label="registered1.5%")
    axes[0].set(
        xlabel="four held-out seeds x eight inputs",
        ylabel="maximum unaligned full-field error (%)",
        title="Whole-field timestep confirmation",
    )
    axes[0].legend()
    axes[1].semilogy(
        [max(r["maximum_error"], 1e-20) for r in result["superposition"]],
        ".",
        label="actual signed-superposition relative error",
    )
    axes[1].axhline(1e-12, ls="--", color="black", label="registered1e-12")
    axes[1].set(
        xlabel="seed/grid/dual polarity",
        ylabel="relative full-field error",
        title="Linear dynamics control",
    )
    axes[1].legend(fontsize=7)
    fig.savefig(out / "experiment_0008_numerical.png")
    plt.close(fig)


def report(root, result):
    verdicts = result["verdicts"]
    text = [
        "# Experiment 0008: energy distribution and lattice communication\n",
        "Registration `8e74e54` and implementation/method `325fe77` preceded all new-seed outcomes. Frozen morphology, unchanged QR6 physics, serial CPU f64. Reference seeds101,103,107,109; held-out127,131,137,139. No new-seed threshold fitting, changed signals, feature selection, seed replacement or held-out refitting.\n",
        "## Separate scientific verdicts\n",
        "| Question | Registered result | Scope |",
        "|---|---|---|",
    ]
    for key in ("P1", "P2", "P3", "P4", "P5", "P6"):
        value = verdicts[key]
        label = json.dumps(value) if isinstance(value, dict) else value
        scope = {
            "P1": "A-only motion reaches ordered distance shells; arrival/peak refinement",
            "P2": "energy participation, non-source motion and cross-module motion at one checkpoint",
            "P3": "S9p versus S27p spatial-energy T; primary distal A4, near A2, secondary A6",
            "P4": "energy sign loss versus signed UV at A2/A4; symmetry independently checked",
            "P5": "ABp versus ABm spatial-energy T; primary distal F4, near F2, secondary F6",
            "P6": "energy, frozen/zero, sign/superposition, repeat and full-field numerical gates",
        }[key]
        text.append(f"| {key} | {label} | {scope} |")
    text.append(
        "\nThe positive communication result is specific: S9p versus S27p per-module spatial energy gives8/8 held-out classifications on BOTH grids at A2 and A4. A4 CROSS also gives8/8 after excluding channels9/27; the global-energy trace gives6/8 and fails. A6 spatial energy fails the absolute separation floor (minimum2.74e-12 versus1e-8) and reaches only6/8. Thus energy reaches shell6, but this six-sensor readout does not retain validated discrimination there.\n"
    )
    text.append(
        "SIGN9/SIGN27 energy-only vectors are identical and yield8 ambiguous held-out cases each; signed UV/all and cross give8/8 at A2/A4. DUAL spatial-energy T gives5/8 at F2 and4/8 at F4, so the registered interaction-discrimination gates fail. Secondary signed UV gives8/8 at F2 but4/8 at F4. Global DUAL energy is INDETERMINATE because its tiny contrast does not clear the numerical-separation margin, despite valid whole-field dynamics. These outcomes concern the fixed readouts; they do not prove every possible distant decoder fails.\n"
    )
    text += [
        "\nThese results are not merged into an overall success score. Propagation, redistribution and discrimination are different questions. No associative memory, internal learning, semantics, emergence, resilience or communication capacity is established.\n",
        "## Execution and definitions\n",
        "97 actual trajectories:64 primary (.025),32 all-held-out confirmations (.0125),1 preselected seed107/ABm repeat. No reused, sign-synthesized or interpolated trajectories. B27p was added before execution as the independent B-source basis; it is not a classifier label. Each nonzero input has actual E0=1; ZERO has E0=0, v0=0. No continuing drive, palette edits or history accumulation. Complete execution status is exported.\n",
        "SourceA2182, sourceB2186; four single inputs S9p/S27p/S9m/S27m and dual ABp/ABm. Same actual initial P within each seed and across grids. Model omega/gamma, cardinal module links, Cubic6 links, split update order, damping and boundary semantics are unchanged. Heterogeneous initialization includes the established special module27 policy; these results are conditional on that initializer.\n",
        "K=.5v^2. Q=onsite plus HALF of every incident edge potential. Actual module mechanical energy is K+Q, not a squared-activity substitute. Motion energy K+onsite excludes edge allocations. At time0 neighboring cells/modules can own half-edge energy with zero local u/v. Arrival therefore uses actual receiver motion energy>=1e-8, while both mechanical and motion crossings are reported. No exact integrated edge-transfer amount is inferred from regional energy change or instantaneous power.\n",
        "Every tick retains global diagnostics,10 region aggregates and50 fixed signed/energy probes. Full P,u,v,K,Q at0,.8,3.2,8,16,32:582 complete checkpoints. Only the5 nonzero times enter the external readout. Earliest crossings and window peaks use actual sampled ticks, no interpolation; a peak at32 need not be a later global maximum.\n",
        "A_d is distance from2182; F_d is minimum distance from either potential source. Receivers exclude both source IDs. Full A4 energy separately includes B's initial allocation and is never called arrival fromA. F4 receivers are at least4 hops from BOTH sources. Geometry-only farthest-point sampling fixes6 decoding probes per region, identical for all seeds/inputs/grids. Full shell statistics and actual all-module spatial partitions are retained independently of those six readout probes.\n",
        "## Energy, transport and spreading\n",
        "![Global energy](figures/experiment_0008_global_energy.png)\n",
        "![Motion arrival and retained-energy fractions](figures/experiment_0008_propagation.png)\n",
        "![Actual spatial energy](figures/experiment_0008_spatial_energy.png)\n",
        "Images use fixed mechanical-energy limits1e-10 to1 (E0), not frame normalization. Log display masks values below its stated display floor only; raw values and scientific thresholds are untouched. The fraction plot explicitly uses currently retained energy; its absolute counterpart prevents relative concentration being mistaken for production.\n",
    ]
    initial = rows(root / "tables/initial_distribution.csv")
    nonzero = [r for r in initial if r["signal"] != "ZERO"]
    text.append(
        f"At initialization nonzero cases have participation {min(float(r['participation']) for r in nonzero):.6f} to {max(float(r['participation']) for r in nonzero):.6f}, yet all non-source motion-active counts are zero. Allocated outside-injected-module energy ranges from {min(float(r['other_energy']) for r in nonzero):.6f} to {max(float(r['other_energy']) for r in nonzero):.6f}; actual outside-module motion is exactly zero. This initial distinction is measured, not called propagation. Every checkpoint's4096-neuron mechanical/motion array is also exported without a viewer.\n"
    )
    text.append(
        f"P1 individual input/shell decisions: {sum(r['verdict'] == 'PASS' for r in result['propagation'])}/{len(result['propagation'])} PASS. P2 held-out input decisions: {sum(r['verdict'] == 'PASS' for r in result['spreading'])}/{len(result['spreading'])} PASS. All failures and each arrival, peak and physical time are in propagation/spreading/arrivals.csv; the report does not replace failed far results with near ones.\n"
    )
    p2 = rows(root / "tables/P2_components.csv")
    text.append(
        f"The P2 failure is concentration, not absence of motion: maximum energy participation across all registered held-out checkpoints and both grids is {max(float(r['participation']) for r in p2):.6f}, below8. Many non-source neurons and other modules do respond. For seed127/S9p at32,170 non-source neurons pass the1e-8 motion threshold, yet participation is only1.448929; for ABm it is4.128305. The registered P2 joint criterion passes0/24 input/seed pairs and is retained unchanged. P2_components.csv exposes every criterion separately.\n"
    )
    text += [
        "## Distinguishability and representation limits\n",
        "Raw external class means use reference seeds only; no virgin subtraction, whitening, feature scaling, per-frame normalization or adaptive selection. Numeric-only vectors exclude labels, IDs, P, seed and condition metadata. A nearest-mean measurement is not a trained internal neural network. Expected classes are evaluated after prediction. Same held-out templates on both grids.\n",
        "G is5 total-energy scalars, inherently global/source-inclusive. SH is5 whole-receiver-region energy sums, with larger spatial coverage disclosed. T and U share the same1920 scalar budget (1860 cross): energy per module versus signed displacement at6 probes. KP and UV share3840 observations (3720 cross): kinetic/potential versus signed displacement/velocity. Comparing T to UV doubles scalar observations and is not called budget-matched. Cross excludes BOTH directly stimulated channels9/27, regardless of input. No near/far features are combined. Higher energy-template accuracy than signed-template accuracy is not a universal information ordering: the fixed nearest-mean method responds differently to a quadratic physics-defined feature map and to raw phase-sensitive coordinates.\n",
        "To pass:>=7/8 correct on each grid, no ties, identical predictions, full-field validity, each feature refinement<=5%, per-seed fine separation above the fixed1e-8 energy /1e-6 signed floor and at least5x coarse/fine disagreement. Invalid physical/feature refinement is INDETERMINATE; below-floor distinguishability FAILS; unresolved separation is INDETERMINATE. Ties count incorrect. See registration for complete priority. Finite paired deterministic cases do not provide a population accuracy or bitrate estimate.\n",
        "| Pair | Global G train | Global G held-out | Fine | Ties held/fine | Verdict (not distal) |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for pair in q.PAIRS:
        item = model(result, pair, "G")
        c = item["counts"]
        text.append(
            f"| {pair} | {c['train']['correct']}/8 | {c['evaluate']['correct']}/8 | {c['refine']['correct']}/8 | {c['evaluate']['ties']}/{c['refine']['ties']} | {item['verdict']} |"
        )
    text += [
        "\n![All-module readouts](figures/experiment_0008_readout_all.png)\n",
        "![Cross-module readouts](figures/experiment_0008_readout_cross.png)\n",
        "Color encodes descriptive accuracy; P/F/I encodes the FULL gated verdict, so correct-but-invalid numerical readouts are not promoted to success. Complete404 model rows,9696 reference/held-out/fine predictions, every error/ambiguity, all distances and per-seed margins are exported in numeric tables. Main selected rows follow; alternative successful rows do not replace a failed primary.\n",
        "| Pair | Region | Mask | Rep/budget | Train | Held-out | Fine | Ties held/fine | Verdict |",
        "|---|---|---|---|---:|---:|---:|---:|---|",
    ]
    for pair in q.PAIRS:
        family = "F" if pair == "DUAL" else "A"
        for d in (2, 4, 6):
            for mask in ("all", "cross"):
                for rep in ("SH", "T", "U", "KP", "UV"):
                    item = model(result, pair, f"{family}{d}_{mask}_{rep}")
                    c = item["counts"]
                    text.append(
                        f"| {pair} | {family}{d} | {mask} | {rep}/{item['dimension']} | {c['train']['correct']}/8 | {c['evaluate']['correct']}/8 | {c['refine']['correct']}/8 | {c['evaluate']['ties']}/{c['refine']['ties']} | {item['verdict']} |"
                    )
    text += [
        "\n## Interaction and numerical reliability\n",
        "![Measured signed interference and actual energy](figures/experiment_0008_interference.png)\n",
        "![Full-field refinement and superposition](figures/experiment_0008_numerical.png)\n",
        "Signed superposition uses independently executed A27p and B27p at the same actual P/dt, scaled by measured amplitude ratios alpha,beta for each dual input. It never adds energy trajectories or assumes1/sqrt2. Quadratic energy cross terms create redistribution even though the underlying dynamics are linear. Sign cancellation is not energy destruction; positive local/edge potentials and damping remain in the balance. Signed maps share one fixed symlog scale from-1.8 to1.8 with a linear interval below1e-6; the display transform never enters features or measurements. No observed interference is called emergence.\n",
    ]
    text.append(
        f"Maximum all-tick numerical drift {100 * max(r['maximum_drift'] for r in result['trajectories'].values()):.8f}% versus1%; full-field refinement max {100 * max(r['maximum_error'] for r in result['refinement'].values()):.8f}% versus1.5%. Sign inversion checked in {len(result['symmetry'])} seed/grid/module comparisons; exact energy stream byte identity in {sum(r['exact_energy_stream_bytes'] for r in result['symmetry'])}. Matched-amplitude superposition max relative error {max(r['maximum_error'] for r in result['superposition']):.8e}. Repeat seed107/ABm reproduces {len(result['repeat_files'])} case files byte-for-byte on this host/compiler. No cross-platform bit identity is promised.\n"
    )
    failed = [r for r in result["refinement"].values() if not r["pass_gate"]]
    text.append(
        "Full-field numerical failures: "
        + (json.dumps(failed) if failed else "none")
        + ". Energy matching, zero input and frozen palettes were checked independently. A bounded energy trace or an attractive image never rescues failed field refinement.\n"
    )
    text += [
        "## Evidence boundaries and reproduction\n",
        "Python independently reconstructs every module energy partition from actual P/u/v, validates all checkpoint region/probe/global measurements, verifies stream timelines/fractions and source identities, computes arrival/spreading from actual every-tick records, checks full signed controls/refinement, fits only reference observations and regenerates every classifier verdict. Every-tick aggregate values are engine observations validated against full fields at registered checkpoints; this is not a second complete ODE integration or a full-state record at every tick. Source-bound caches bind every input byte.\n",
        "The authored mechanical units and absolute detection floors are experimental conventions; there is no real sensor-noise or physical-material validation. Failure of a fixed class-mean readout alone does not prove every possible readout fails. By contrast, the explicitly tested even-energy/odd-signed inversion symmetry establishes the prescribed sign ambiguity within this frozen model. Energy arrival, multi-neuron spread and useful remote discrimination remain separate.\n",
        "Earlier QR4/QR5 timestep failures and QR7 adaptive R3 failure are unchanged. Frozen QR8 findings do not validate plasticity, recall, associations, capacity, interference tolerance, resilience or Principle 002 as an experimentally established law. Principle 002 is a proposed mechanism, not an experimentally established law.\n",
        "See [registration](../EXPERIMENT_0008.md), [schema](EXPERIMENT_0008_SCHEMA.md) and [README reproduction commands](../README.md). Raw observations, full ledger, source/data manifests, references and viewer-free review/data/full-field archives remain ignored under results/experiment_0008 and are copied to Downloads at delivery. Source checks, local measurements, remote commit and hosted CI are reported separately. No Bevy window, GPU physics, viewer modification or FPS claim was needed.\n",
    ]
    Path("docs/EXPERIMENT_0008_RESULTS.md").write_text("\n".join(text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = json.loads((args.root / "verification.json").read_text())
    for item in result["trajectories"].values():
        q.CHECKED.update(item["frames"])
    export(args.root, result)
    plots(args.root, result, Path("docs/figures"))
    report(args.root, result)
    print("Generated QR8 report, complete tables and seven measured-data figures")


if __name__ == "__main__":
    main()
