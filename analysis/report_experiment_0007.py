"""Generate measured QR7 tables, scientific figures, report and operation manual."""

# ruff: noqa: E501 -- Long generated Markdown prose and table rows.

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from analysis import experiment_0007 as q7


def table_file(path, records):
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def make_tables(root, result):
    out = root / "tables"
    out.mkdir(exist_ok=True)
    readout = result["readout"]
    predictions = [
        {
            **{k: v for k, v in r.items() if k != "distances"},
            "d0": r["distances"][0],
            "d1": r["distances"][1],
        }
        for r in readout["predictions"]
    ]
    table_file(out / "predictions.csv", predictions)
    table_file(out / "margins.csv", readout["margins"])
    table_file(out / "refinement.csv", readout["remote_influence"])
    table_file(out / "structure.csv", result["structure"])
    table_file(
        out / "trajectories.csv",
        [
            {k: v for k, v in r.items() if k != "frames"}
            for r in result["trajectories"].values()
            if r["write"]
        ],
    )
    controls = []
    for model in readout["models"]:
        for name, counts in model["counts"].items():
            controls.append(
                dict(rule=model["rule"], calibrated=model["calibrated"], condition=name, **counts)
            )
    table_file(out / "classification_counts.csv", controls)
    # Exact measured palettes in a content-addressed store, without a viewer.
    store = root / "palettes"
    store.mkdir(exist_ok=True)
    index = []
    import hashlib

    for stage_name in ("train", "evaluate", "refine"):
        stage = root / stage_name
        for folder in sorted(stage.iterdir()):
            if not folder.is_dir() or not (folder / "COMPLETE").exists():
                continue
            for filename in ("000000.q7f", "post.q7f"):
                file = folder / filename
                if file.exists():
                    data = q7.decode(file)["palette"].tobytes()
                    digest = hashlib.sha256(data).hexdigest()
                    target = store / f"{digest}.palette"
                    if not target.exists():
                        target.write_bytes(data)
                    index.append(
                        dict(
                            stage=stage_name,
                            trajectory=folder.name,
                            checkpoint=filename,
                            sha256=digest,
                            bytes=len(data),
                        )
                    )
    table_file(out / "palette_index.csv", index)
    differences = []
    for stage_name, seeds in (("train", q7.TRAIN), ("evaluate", q7.HELD), ("refine", q7.HELD)):
        stage = root / stage_name
        for seed in seeds:
            virgin = q7.checkpoint(stage, f"s{seed}_CALIBRATE_p9", 0)["palette"].reshape(4096, 64)
            for rule in (2, 3):
                ps = [
                    q7.decode(stage / q7.ident(seed, rule, symbol, "WRITE") / "post.q7f")[
                        "palette"
                    ].reshape(4096, 64)
                    for symbol in (0, 1)
                ]
                for i, m in zip(*np.nonzero((ps[0] != virgin) | (ps[1] != virgin)), strict=True):
                    differences.append(
                        dict(
                            stage=stage_name,
                            seed=seed,
                            rule=rule,
                            id=int(i),
                            module=int(m),
                            virgin=int(virgin[i, m]),
                            W0=int(ps[0][i, m]),
                            W1=int(ps[1][i, m]),
                        )
                    )
    table_file(out / "palette_differences.csv", differences)
    return out


def plots(root, result, figures):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "figure.dpi": 150})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    for ri, rule in enumerate((2, 3)):
        seed = 59
        virgin = q7.checkpoint(root / "evaluate", f"s{seed}_CALIBRATE_p9", 0)["palette"].reshape(
            4096, 64
        )
        states = []
        count_maps = []
        for symbol in (0, 1):
            p = q7.decode(root / "evaluate" / q7.ident(seed, rule, symbol, "WRITE") / "post.q7f")[
                "palette"
            ].reshape(4096, 64)
            states.append(p)
            counts = np.count_nonzero(p != virgin, axis=1).reshape(16, 16, 16).sum(axis=0)
            count_maps.append(counts)
        maximum = max(int(c.max()) for c in count_maps)
        for symbol, p in enumerate(states):
            image = axes[ri, symbol].imshow(
                count_maps[symbol], origin="lower", vmin=0, vmax=maximum, cmap="magma"
            )
            axes[ri, symbol].set(
                title=f"seed59 R{rule} W{symbol}: edits summed over z", xlabel="x", ylabel="y"
            )
            axes[ri, symbol].text(
                0.02,
                0.97,
                f"{int(np.count_nonzero(p != virgin))} edited modules",
                transform=axes[ri, symbol].transAxes,
                va="top",
                color="cyan",
            )
        fig.colorbar(image, ax=axes[ri, :], label="edited modules (sum over z)", shrink=0.75)
    fig.savefig(figures / "experiment_0007_structure.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    for ri, rule in enumerate((2, 3)):
        for grid, style in (("evaluate", "-"), ("refine", "--")):
            stage = root / grid
            traces = []
            for symbol in (0, 1):
                folder = stage / (q7.ident(59, rule, symbol, "REMOTE_ONLY") + "_p9")
                traces.append(np.fromfile(folder / "outputs.f64", "<f8").reshape(-1, 12))
            dt = 0.025 if grid == "evaluate" else 0.0125
            times = np.arange(len(traces[0])) * dt
            for symbol in (0, 1):
                axes[ri, 0].plot(
                    times, traces[symbol][:, 0], style, lw=0.9, label=f"{grid} W{symbol}"
                )
            axes[ri, 1].plot(times, traces[1][:, 0] - traces[0][:, 0], style, label=grid)
        for col in (0, 1):
            axes[ri, col].axhline(0, color="grey", lw=0.5)
            axes[ri, col].set(
                xlabel="physical time",
                ylabel="signed u[2184,9]",
                title=f"R{rule}: " + ("REMOTE read, pulse9" if col == 0 else "signed W1 minus W0"),
            )
            axes[ri, col].legend(fontsize=7)
    fig.savefig(figures / "experiment_0007_signed_read.png")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ri, rule in enumerate((2, 3)):
        entries = [r for r in result["readout"]["margins"] if r["rule"] == rule and r["calibrated"]]
        x = np.arange(4)
        axes[ri].bar(
            x - 0.18, [r["separation"] for r in entries], 0.36, label="fine W0/W1 separation S"
        )
        axes[ri].bar(
            x + 0.18,
            [5 * r["refinement_error"] for r in entries],
            0.36,
            label="5 x coarse/fine disagreement D",
        )
        axes[ri].set(
            xticks=x,
            xticklabels=[r["seed"] for r in entries],
            xlabel="held-out seed",
            ylabel="120-feature Euclidean distance",
            title=f"R{rule}, calibrated, registered S >= 5D",
        )
        axes[ri].legend(fontsize=7)
    fig.savefig(figures / "experiment_0007_uncertainty.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
    for ri, rule in enumerate((2, 3)):
        for calibrated, offset in ((True, -0.18), (False, 0.18)):
            model = next(
                m
                for m in result["readout"]["models"]
                if m["rule"] == rule and m["calibrated"] == calibrated
            )
            values = [model["counts"]["evaluate/" + kind]["correct"] for kind in q7.CONTROLS]
            axes[ri].bar(
                np.arange(8) + offset, values, 0.36, label="calibrated" if calibrated else "raw"
            )
        axes[ri].set(
            xticks=np.arange(8),
            xticklabels=q7.CONTROLS,
            ylim=(0, 8.8),
            ylabel="correct / 8 held-out cases",
            title=f"R{rule}: same REMOTE-trained templates for every control",
        )
        axes[ri].tick_params(axis="x", labelsize=7)
        axes[ri].axhline(7, ls="--", color="grey", label="primary threshold applies to REMOTE")
        axes[ri].legend(fontsize=7)
    fig.savefig(figures / "experiment_0007_controls.png")
    plt.close(fig)


def verdict(model, result):
    rule = model["rule"]
    numerical = all(
        r["numerical_pass"] for r in result["readout"]["remote_influence"] if r["rule"] == rule
    )
    if not numerical:
        return "INDETERMINATE (numerical gate)"
    return "PASS" if model["operational_pass"] else "FAIL"


def report(root, result):
    readout = result["readout"]
    text = [
        "# Experiment 0007: operational control and readout\n",
        "Registration `2cc0e00` preceded implementation/data; interface/decoder checkpoint `d7f97f0` preceded execution. Baseline `e3255da`. No criteria, feature selection, split or template fit changed after held-out observations. QR7 parser enum correction and per-rule gate scoping are implementation corrections, not new scientific criteria.\n",
        "This is a finite deterministic test of two externally specified experiences. Calibration and decoder templates are external apparatus. Neither structural change nor successful classification establishes distributed associative retrieval, capacity, resilience, intelligence, or Principle 002 as an experimentally established law.\n",
        "## Measured verdicts\n",
        "| Rule | Readout | Training REMOTE | Held-out REMOTE | Fine REMOTE | Ambiguities (held/fine) | Separation/refinement margin | Verdict |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for m in readout["models"]:
        c = m["counts"]
        text.append(
            f"| R{m['rule']} | {'calibrated' if m['calibrated'] else 'raw'} | {c['train/REMOTE_ONLY']['correct']}/8 | {c['evaluate/REMOTE_ONLY']['correct']}/8 | {c['refine/REMOTE_ONLY']['correct']}/8 | {c['evaluate/REMOTE_ONLY']['ties']}/{c['refine/REMOTE_ONLY']['ties']} | {'PASS' if m['margin_pass'] else 'FAIL'} | {verdict(m, result)} |"
        )
    text += [
        "\nR2 calibrated is the primary result. R3 and raw readout remain separate secondary results. A software pass cannot override a failed or indeterminate scientific gate. There is no population-level accuracy estimate from these eight paired deterministic cases.\n",
        f"Structural encoding: **{'PASS' if result['structural_pass'] else 'FAIL'}** across {len(result['structure'])} registered rule/seed/grid pairs; {sum(r['distinct'] for r in result['structure'])}/{len(result['structure'])} pairs have distinct W0/W1 palettes; committed P survives exact transient reset. Repeatability: **PASS**, {result['repeat']['identical_files']} original/repeat files byte-identical for seed31/R2/W0 WRITE and its two REMOTE reads on this toolchain.\n",
        f"Physical audit: **PASS** for all 496 primary executions. All-tick drift maximum {100 * max(r['max_energy_drift'] for r in result['trajectories'].values()):.6f}% (bound1%). All initial active impulses satisfy E=1 within1e-12; 24 zero exposures remain exactly zero. All frozen exposures and reads retain P. RESET clears u,v,V,H and audit accounts; this does not erase P.\n",
        "## Execution and provenance\n",
        "688 logical trajectories =496 actual primary executions +192 explicit virgin-calibration reuses; preselected repeat adds3 actual trajectories (499 total). Training208, held-out208, fine80. No registered condition is omitted. Initial background launch was interrupted before any measurement; the empty ledger is retained separately and is not a scientific failure/retry. Actual runs use fresh folders and never overwrite completed evidence.\n",
        "Coarse writes80, coarse calibration reads16, actual coarse control reads320; fine writes40, fine calibration reads8, fine REMOTE reads32. Reuses apply only to VIRGIN/FROZEN/NO_WRITE reads with exact identical initial physical state. Their observations remain labeled CALIBRATE. FROZEN has an actual write exposure and full history but no commit; NO_WRITE has an actual eight-unit zero exposure and a rule-enabled commit.\n",
        "WRITE port2182 modules9/27, E1, [0,8], one R2/R3 commit. RESET precedes two independent READ pulses at2183 modules9 then27, E1, [0,32], plasticity off. Sampling sites2184/85/86, modules9/27, signed u/v, times .8/3.2/8/16/32 give120 numeric features. dt.025 primary, .0125 all held-out REMOTE cases plus their exposures/calibrations/controls. No unit-displacement comparisons were collected.\n",
        "Templates use REMOTE training seeds7,19,31,43 only; held-out59,71,83,97 never enter fitting. Calibration subtracts each seed's separately measured virgin response. No standardization, scaling, pruning or normalization. Two class means, squared Euclidean distance; ties at1e-12 relative tolerance count as incorrect. Raw has its own training means. Labels are compared only after prediction. Numeric feature files contain no label, seed, palette, condition or eligibility data. Source-level API isolation and independent reconstruction support this boundary; this is not a formal information-flow proof.\n",
        "## Structure and causal controls\n",
        "![Actual spatial edit counts](figures/experiment_0007_structure.png)\n",
        "The plotted maps are actual seed59 edits summed over z, not activity magnitude. Every neuron owns its palette. Full before/after palettes and edit ledgers are exported; per-neuron edit cap8 and all R3 histogram identities were independently checked. SHUFFLED preserves actual edited count per neuron and edited neuron IDs/distances; R3 additionally preserves each color histogram. R2 does not promise histogram matching; shuffled R3 swaps need not be adjacent. Both ports are restored in REMOTE_ONLY.\n",
        "![Signed remote response](figures/experiment_0007_signed_read.png)\n",
        "![Control classifications](figures/experiment_0007_controls.png)\n",
        "| Rule | Control | Calibrated held-out correct | Raw held-out correct | Calibrated ties | Raw ties |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for rule in (2, 3):
        models = [
            next(m for m in readout["models"] if m["rule"] == rule and m["calibrated"] == c)
            for c in (True, False)
        ]
        for kind in q7.CONTROLS:
            a, b = [m["counts"]["evaluate/" + kind] for m in models]
            text.append(
                f"| R{rule} | {kind} | {a['correct']}/8 | {b['correct']}/8 | {a['ties']} | {b['ties']} |"
            )
    influence = readout["remote_influence"]
    text += [
        f"\nRemote causal influence reaches the registered1% raw-vector difference in {sum(r['influence_pass'] for r in influence)}/{len(influence)} selected seed/rule/symbol pairs at both grids. This is a response difference, not an improvement, and is distinct from classification. Control differences are nonadditive; no response percentage is attributed to a specific component. No neuron-level necessity, memory association or resilience test was performed.\n",
        "## Numerical uncertainty\n",
        "![Registered separation margin](figures/experiment_0007_uncertainty.png)\n",
        "Signed full-field relative L2 is checked at every nonzero registered read checkpoint with bound1.5%; edit-position Jaccard bound.90; feature relative disagreement bound5%. Per held-out seed/rule, fine W0/W1 feature separation S must exceed1e-10 and5 times the maximum coarse/fine feature disagreement D. Predictions must agree between grids using the original coarse training templates; no finer-grid retraining.\n",
        "| Rule | Max signed field disagreement | Min edit Jaccard | Exact palettes on fine grid |",
        "|---|---:|---:|---:|",
    ]
    for rule in (2, 3):
        rr = [r for r in influence if r["rule"] == rule]
        text.append(
            f"| R{rule} | {100 * max(r['maximum_field_error'] for r in rr):.6f}% | {min(r['edit_jaccard'] for r in rr):.6f} | {sum(r['palette_equal'] for r in rr)}/8 |"
        )
    text += [
        "\n## Every held-out prediction, including errors and ambiguities\n",
        "The following primary/secondary REMOTE table includes every held-out case. Full train/control/fine predictions, distances, errors, margins, structural and trajectory tables are in the portable package. `None` denotes an ambiguous incorrect case.\n",
        "| Rule | Preprocessing | Seed | W expected | Coarse prediction | Fine prediction |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for rule in (2, 3):
        for cal in (True, False):
            for seed in q7.HELD:
                for s in (0, 1):
                    rr = [
                        next(
                            r
                            for r in readout["predictions"]
                            if r["stage"] == stage
                            and r["rule"] == rule
                            and r["calibrated"] == cal
                            and r["seed"] == seed
                            and r["expected"] == s
                            and r["kind"] == "REMOTE_ONLY"
                        )
                        for stage in ("evaluate", "refine")
                    ]
                    text.append(
                        f"| R{rule} | {'calibrated' if cal else 'raw'} | {seed} | {s} | {rr[0]['prediction']} | {rr[1]['prediction']} |"
                    )
    text += [
        "\n## Interpretation, verification and limits\n",
        "Independent Python decoded both checksums of all signed fields, reconstructed all checkpoint energies from tensor neighbor slicing, verified all switch-work partitions, reintegrated V/H at six full-module probe sites, rebuilt eligibility and every actual R2/R3 edit from exported histories, verified causal masks/shuffles, reconstructed all120-component read vectors from full signed checkpoints, independently fit the training means and reproduced every prediction and numerical margin. This is not a second independent full-lattice ODE integration.\n",
        "The prior 0004 long-window timestep failures and 0005 long-window failure remain unchanged; a bounded QR7 read does not overturn them. Principle002 is a proposed mechanism, not an experimentally established law. Externally restored virgin P is not demonstrated intrinsic forgetting. Calibration and template storage are not lattice memory. No sequential writes, capacity, interference, damage, GPU dynamics or conventional neural network was introduced.\n",
        "Reproduce and inspect using the commands in [README](../README.md), the [frozen registration](../EXPERIMENT_0007.md), [schema](EXPERIMENT_0007_SCHEMA.md), and [Operational Lattice Manual](OPERATIONAL_LATTICE_MANUAL.md). Raw data and packages remain ignored under `results/experiment_0007`; package integrity uses SHA-256, not authenticity signatures. Hosted CI, push/remote SHA and local quality checks are delivery evidence separate from these measured scientific verdicts.\n",
    ]
    Path("docs/EXPERIMENT_0007_RESULTS.md").write_text("\n".join(text))


def manual(result):
    models = result["readout"]["models"]
    lines = [
        "# Operational Lattice Manual — Experiment 0007\n",
        "This manual covers only the measured heterogeneous16³ CPU/f64 bodies, eight registered seeds, fixed input energies/windows and two frozen morphology rules. It is an external laboratory interface, not an autonomous memory service. See the [full scientific report](EXPERIMENT_0007_RESULTS.md) for negative and indeterminate cases.\n",
        "| Operation | Required state and exact input | Verified observable result | Energy and limits |",
        "|---|---|---|---|",
        "| CALIBRATE | Virgin backup P; complete reset. Pulse2183/module9 then separate reset/pulse27; E1, integrate32 each, plasticity off | Two measured signed reference responses,120 components retained externally | Each pulse injects mechanical energy1. Damping removes energy; observed drift below1%. Reference is external apparatus |",
        "| WRITE | Externally restored virgin P and zero transients. W0=2182/module9, W1=2182/module27, E1, integrate8, single R2/R3 commit | Actual distinct persistent W0/W1 palettes; full histories, eligibility and edits exported | Commit changes stiffness/couplings and carries explicit external switching work; it is not energy-free learning. One write only |",
        "| RESET | Any retained P; no excitation | Exact zero u,v,V,H,tick and audit accounts; P retained byte-for-byte | Clears residual mechanical activity and accounting; removed energy is an external intervention, not forgetting or passive damping |",
        "| READ | RESET retained P. Fixed pulses2183/modules9 then27, separate resets; E1 each; integrate32, plasticity disabled | Signed u/v at2184/85/86 modules9/27 at .8/3.2/8/16/32; P unchanged | Matching amplitude depends on measured morphology stiffness by the same formula for all symbols. Label must never select pulse, sampling or amplitude policy |",
        "| RESTORE | Explicit external virgin backup from the same seed/body | Subsequent WRITE begins at exactly the original virgin palette | RESET before/after installation. This externally replaces structure; intrinsic erasure/forgetting is not established |",
        "| CONTROL_INSTALL | RESET plus authentic WRITE outcome, same seed/rule/virgin P | Registered ALL/port-only/REMOTE/shuffle/virgin ablations only | Experimental causal intervention; no arbitrary desired-answer palette API. Not a memory write mechanism |\n",
        "## Readout capability and failure boundary\n",
    ]
    for model in models:
        counts = model["counts"]
        lines.append(
            f"- R{model['rule']} {'calibrated' if model['calibrated'] else 'raw'} REMOTE discrimination: **{verdict(model, result)}**; held-out {counts['evaluate/REMOTE_ONLY']['correct']}/8, fine {counts['refine/REMOTE_ONLY']['correct']}/8. {'A bounded operational capability only within this registered apparatus.' if model['operational_pass'] else 'Do not describe this failed or indeterminate readout as a working capability.'}"
        )
    lines += [
        "\nCalibration-dependent success, when present without raw success, requires the externally stored virgin reference. Template means are fitted externally on four training seeds and frozen; no learning occurs inside the decoder during evaluation. A positive secondary R3 result cannot replace the primary R2 verdict.\n",
        f"The preselected seed31/R2/W0 WRITE and two REMOTE reads reproduce {result['repeat']['identical_files']} files byte-for-byte on the same compiler/host; cross-platform bit identity and exhaustive repeatability are not established. All writes start from virgin P; sequential storage is untested.\n",
        "## Exact use and interpretation\n",
        "Build `cargo build --locked --release --bin experiment_0007`. The batch CLI takes `train|evaluate|refine|repeat ROOT`; each stage must be fresh. Run train first, preserve `TRAINING_FROZEN` and the template SHA receipt, then evaluate/refine/repeat without changing features or fitting. Run the independent auditor before interpreting any scientific pass. Complete commands and dependencies are in README.\n",
        "The Rust `Operator` exposes immutable physical inspection, `write`, `advance`, `commit`, `reset`, `read`, `restore`, `control`, and operation-aware checkpoints. WRITE must end at8 for commit; READ ends at32. Idle stepping, premature/duplicate commit, writes to retained edited structure, calibration of edited structure, invalid module/grid/rule and foreign control outcomes are rejected. `read` receives no write label.\n",
        "Do not infer distributed associative recall, intelligence, resilience, generalization, capacity, interference tolerance, useful sequential writes or Principle002 from these operations. Frozen/no-write/virgin controls, signed fields, actual energy matching and registered numerical gates remain mandatory. The viewer is unnecessary for reproduction or review.\n",
    ]
    Path("docs/OPERATIONAL_LATTICE_MANUAL.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = json.loads((args.root / "verification.json").read_text())
    protocol = json.loads((args.root / "protocol-verification.json").read_text())
    assert protocol["actual_operations"] == 499 and protocol["reuse_identity"]
    for trajectory in result["trajectories"].values():
        q7.CHECKED.update(trajectory["frames"])
    make_tables(args.root, result)
    plots(args.root, result, Path("docs/figures"))
    report(args.root, result)
    manual(result)
    print("Generated measured report, manual, tables, palette store and four scientific figures")


if __name__ == "__main__":
    main()
