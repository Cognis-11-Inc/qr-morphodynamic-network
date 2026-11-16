"""Render measured QR9 standalone validation; no numerical gate is changed here."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

from analysis import experiment_0009 as q


def save(fig, name):
    path = Path("docs/figures") / ("experiment_0009_" + name + ".png")
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root
    verdict = json.loads((root / "verification.json").read_text())
    rho, sound, bulk, mu = q.reference()
    joules = 1e-12 * sound**2
    pressure_scale = np.sqrt(bulk * joules)
    velocity_scale = np.sqrt(joules / rho)
    fig, axes = plt.subplots(3, 2, figsize=(13, 9), constrained_layout=True)
    for row, mode in enumerate(q.MODES[:3]):
        for n, dt in q.GRIDS:
            folder = root / f"{q.fixture_name(mode)}_n{n}_dt{dt}"
            series = q.rows(folder / "probes.csv")[3::21]
            time = np.array([float(x["tick"]) * dt / sound for x in series])
            p = np.array([float(x["q"]) * pressure_scale for x in series])
            label = f"N{n},dt{dt}/c"
            axes[row, 0].plot(time * 1000, p, label=label, alpha=0.7)
            freq = np.fft.rfftfreq(len(p) - 1, dt / sound)
            spectrum = abs(np.fft.rfft(p[:-1])) * 2 / (len(p) - 1)
            axes[row, 1].plot(freq, spectrum, label=label, alpha=0.7)
        axes[row, 0].set(
            title=f"{['LOW', 'MID', 'HIGH'][row]} actual standing-wave pressure",
            ylabel="Pa",
            ylim=(-80, 80),
        )
        axes[row, 1].set(
            title="Recorded spectrum; no frame normalization",
            ylabel="Pa",
            xlim=(0, 500),
            ylim=(0, 80),
        )
        axes[row, 1].axvline(sound * mode[0] / 48, color="black", ls="--", lw=0.8)
        axes[row, 0].legend(fontsize=8)
    axes[-1, 0].set_xlabel("physical time (ms)")
    axes[-1, 1].set_xlabel("frequency (Hz)")
    save(fig, "waveforms")

    summaries = q.rows(root / "case_summary.csv")
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), constrained_layout=True)
    for index, (n, dt) in enumerate(q.GRIDS):
        names = [f"{q.fixture_name(mode)}_n{n}_dt{dt}" for mode in q.MODES]
        selected = [next(x for x in summaries if x["case"] == name) for name in names]
        x = np.arange(4) + (index - 1) * 0.24
        axes[0].bar(
            x, [float(s["continuum_max"]) * 100 for s in selected], width=0.23, label=f"N{n},dt{dt}"
        )
        axes[1].bar(x, [float(s["time_max"]) * 100 for s in selected], width=0.23)
        axes[2].bar(x, [float(s["drift"]) * 100 for s in selected], width=0.23)
    for ax, title in zip(
        axes,
        (
            "Full continuum field error",
            "Error relative to semidiscrete solution",
            "Actual energy drift",
        ),
        strict=True,
    ):
        ax.set(
            title=title,
            ylabel="percent",
            xticks=range(4),
            xticklabels=("LOW", "MID", "HIGH", "diagonal"),
        )
    axes[0].legend(fontsize=8)
    save(fig, "numerical")

    gates = q.rows(root / "gates.csv")
    names = [s["case"] for s in summaries]
    discrepancies = [
        max(
            float(g["value"])
            for g in gates
            if g["case"] == name and g["gate"].startswith("energy_reconstruction")
        )
        for name in names
    ]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    axes[0].bar(range(len(names)), np.maximum(discrepancies, 1e-17))
    axes[0].axhline(1e-12, color="red", ls="--", label="frozen 1e-12 bound")
    axes[0].set(
        yscale="log",
        ylabel="relative energy-report discrepancy",
        xticks=range(len(names)),
        xticklabels=names,
        title="Recorded summation failures",
    )
    axes[0].tick_params(axis="x", labelrotation=90, labelsize=7)
    axes[0].legend(fontsize=8)
    reductions = [g for g in gates if g["gate"] == "spatial_error_reduction"]
    axes[1].bar(range(4), [float(g["value"]) for g in reductions])
    axes[1].axhline(0.35, color="red", ls="--", label="required ≤0.35")
    axes[1].set(
        xticks=range(4),
        xticklabels=("LOW", "MID", "HIGH", "diagonal"),
        ylabel="fine / primary maximum field error",
        title="Registered refinement reduction",
    )
    axes[1].legend()
    save(fig, "failed_gates")

    fig, axes = plt.subplots(3, 4, figsize=(15, 10), constrained_layout=True)
    for col, time in enumerate(q.TIMES):
        f = q.decode(root / f"gaussian_n48_dt0.05/{round(time / 0.05):06}.q9a")
        field = f["fields"]
        # Fixed z=11.75 m slice. Face velocities are averaged onto pressure centres.
        centred = []
        for axis in range(3):
            w = field[axis + 1]
            lower = np.roll(w, 1, axis=2 - axis)
            boundary = [slice(None)] * 3
            boundary[2 - axis] = 0
            lower[tuple(boundary)] = 0
            centred.append(0.5 * (w + lower))
        speed = np.sqrt(np.sum(np.array(centred) ** 2, axis=0))
        planes = (
            field[0][23] * pressure_scale,
            speed[23] * velocity_scale,
            q.density(field)[23] * joules,
        )
        for row, plane in enumerate(planes):
            options = (
                {"cmap": "RdBu_r", "vmin": -80, "vmax": 80}
                if row == 0
                else {"cmap": "viridis", "vmin": 0, "vmax": 5e-5}
                if row == 1
                else {"cmap": "magma", "norm": LogNorm(1e-14, 3e-6)}
            )
            axes[row, col].imshow(
                np.maximum(plane, 1e-30) if row == 2 else plane,
                origin="lower",
                extent=(0, 24, 0, 24),
                **options,
            )
            axes[row, col].set_title(f"t={time / sound * 1000:.3f} ms")
            if col == 0:
                axes[row, col].set_ylabel(
                    ("pressure (Pa)", "particle speed (m/s)", "energy density (J/m³)")[row]
                    + "\ny (m)"
                )
            axes[row, col].set_xlabel("x (m)")
        if col == 3:
            for row in range(3):
                fig.colorbar(axes[row, col].images[0], ax=axes[row, :], shrink=0.65)
    save(fig, "gaussian_fields")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    probe_rows = q.rows(root / "gaussian_n48_dt0.05/probes.csv")
    for distance in (2, 4, 6):
        series = [x for x in probe_rows if int(x["axis"]) == 0 and float(x["offset"]) == distance]
        time = np.array([float(x["tick"]) * 0.05 / sound for x in series])
        p = np.array([float(x["q"]) * pressure_scale for x in series])
        axes[0].plot(time * 1000, p, label=f"nominal {distance} m")
        axes[1].plot(distance, max(abs(p)), "o", label=f"{distance} m")
    axes[0].set(
        title="Actual Gaussian pressure probes (+x)", xlabel="physical time (ms)", ylabel="Pa"
    )
    axes[1].set(
        title="Window-peak pressure versus distance", xlabel="nominal distance (m)", ylabel="Pa"
    )
    axes[0].legend()
    axes[1].text(
        0.03,
        0.95,
        "Gaussian pulse, no neural source.\nNot material absorption or transmitted flux.",
        transform=axes[1].transAxes,
        va="top",
        fontsize=9,
    )
    save(fig, "gaussian_probes")

    failed = verdict["failures"]
    lines = [
        "# Experiment 0009: saline acoustic container — standalone gate results",
        "",
        "The frozen standalone prerequisite was executed and independently audited. "
        + (
            "It failed; the registered stopping rule prevents neural coupling or neural confirmation."  # noqa: E501
            if failed
            else "It passed; coupled stages remain pending."
        ),
        "",
        "## Independent verdicts",
        "",
        "| Question | Verdict | Evidence boundary |",
        "|---|---|---|",
    ]
    for label, name in (
        ("S1", "Acoustic solver validity"),
        ("S2", "Reciprocal coupling"),
        ("S3", "Distance-dependent neural transmission"),
        ("S4", "Frequency-dependent neural communication"),
        ("S5", "Remote S9/S27 discrimination"),
        ("S6", "DIRECT/FLUID/HYBRID comparison"),
        ("S7", "Immersed-population spatial distribution"),
        ("S8", "Numerical reliability"),
    ):
        result = (
            verdict["S1"]
            if label == "S1"
            else "FAIL"
            if label == "S8" and failed
            else "INDETERMINATE"
        )
        reason = (
            "Registered standalone gates below"
            if label in ("S1", "S8")
            else "NOT RUN: prerequisite stopping rule"
        )
        lines.append(f"| {label}: {name} | {result} | {reason} |")
    lines += [
        "",
        "No overall success score. S1 FAIL means the solver did not satisfy this registration; it does not establish that acoustic communication is impossible. No QR neuron was coupled to the fluid, no acoustic S9/S27 decoder was fitted, and no 0008 improvement is claimed.",  # noqa: E501
        "",
        "## Freeze, execution and independent checks",
        "",
        "Registration17ee680 and implementation/methodc07dac9 both preceded execution. No thresholds, numerical grids, initial conditions or analytic formulas were changed after observations. Baseline5fd2794 remains preserved. All17 executions completed: five fixtures on three grids, ZERO and the independent HIGH repeat. Complete q/w at0,6,12,24:68 checkpoints. Every-tick metrics/probes and all failures remain in the raw archive. Full-population253 scientific plus192 work calibrations were conditional; all445 are NOT RUN.",  # noqa: E501
        "",
        f"Independent Python reconstructed {verdict['gates']} scalar gates; {len(failed)} failed. It checks full continuum and semidiscrete fields, true co-timed energy and its face partition, probe samples, projections, boundary slots, Gaussian reflection/permutation symmetry, zero and repeat. This is analytic field comparison and reconstruction, not a second full fluid integration.",  # noqa: E501
        "",
        "## Physical assumptions and reference properties",
        "",
        f"T20 C, nominal S35g/kg, reference atmospheric pressure. Computed rho={rho:.12f}kg/m³, c={sound:.9f}m/s, adiabatic K={bulk:.6f}Pa, mu={mu:.12g}Pa s. These are referenced correlations, not new property measurements. See the [frozen registration](../EXPERIMENT_0009.md) for equations, validity ranges, scale distinctions and primary citations. The model is conservative: viscosity/thermal/chemical absorption are disabled. Its seawater reference does not make it a complete dissipative seawater model.",  # noqa: E501
        "",
        f"Engineered mapping: L*=1m, M*=1kg/module, U*=1µm, t*={1 / sound:.12g}s, E*={joules:.12g}J. Pressure scale {pressure_scale:.9g}Pa, particle-velocity scale{velocity_scale:.9g}m/s. LOW/MID/HIGH={sound / 12:.6f}/{sound / 8:.6f}/{sound / 6:.6f}Hz; wavelengths12/8/6m. These hertz depend on the engineered mapping. Domain24³m³; rigid reflecting walls; time horizon{24 / sound * 1000:.9f}ms. No whale-like range inference.",  # noqa: E501
        "",
        "N48 h.5m dt.05/c; temporal N48 dt.025/c; spatial N96 h.25m dt.025/c. At the shortest carrier wavelength12/24 points and120/240 samples per period. Fourth-order interior staggered gradient, exact negative-transpose divergence, symmetric second-order time split. No numerical clipping or per-frame normalization.",  # noqa: E501
        "",
        "## Recorded gate failures",
        "",
        "| Fixture | Gate | Measured | Frozen limit |",
        "|---|---|---:|---:|",
    ]
    for g in failed:
        lines.append(f"| {g['case']} | {g['gate']} | {g['value']:.12g} | {g['limit']:.12g} |")
    diagnosis = json.loads((root / "diagnosis.json").read_text())
    e = diagnosis["energy"]
    worst_disagreement = max(
        g["value"] for g in failed if g["gate"].startswith("energy_reconstruction")
    )
    lines += [
        "",
        "![Failed energy-report and refinement gates](figures/experiment_0009_failed_gates.png)",
        "",
        "## Post-outcome causal diagnosis — original failures retained",
        "",
        f"The worst energy-report disagreement is {worst_disagreement:.12g} relative. "
        f"For {e['case']} at t={e['time']:g}, recorded energy={e['recorded']:.15f}; "
        f"repeating ordinary serial summation reproduces that value exactly. "
        f"Accurate math.fsum gives {e['math_fsum']:.15f}, while NumPy pairwise gives "
        f"{e['numpy_pairwise']:.15f} (agreement {e['pairwise_fsum_relative']:.3g} relative). "
        "This identifies accumulated summation roundoff in the reported total. It does not "
        "remove the failed reconstruction gates or establish an unmeasured coupled energy balance.",
        "",
        "The LOW combined space/time refinement ratio is0.869709162085, above0.35. "
        "Its primary continuum error0.00832961% becomes0.00724434% on the spatial-fine "
        "grid. The primary result benefits from cancellation between spatial and temporal "
        "dispersion errors. Time refinement alone raises this continuum error to0.01858750%, "
        "while its error against the exact semidiscrete solution falls by about4x. "
        "Thus small absolute error does not establish the registered convergence ratio.",
        "",
        "An analytic check after seeing the failures predicts all12 modal/grid maximum "
        "errors within1e-10 absolute, without another simulation: for semidiscrete frequency "
        "omega_h, split frequency=2asin(dt*omega_h/2)/dt; pressure coefficient=cos(omega_split*t), "
        "velocity coefficient=sin(omega_split*t)/sqrt(1-(dt*omega_h/2)²). Comparing these with "
        "the continuum coefficients reproduces the cancellation and its change on refinement. "
        "This diagnostic is post-outcome, not a replacement acceptance criterion. The source "
        "analysis/diagnose_experiment_0009.py and all numerical values are packaged.",
    ]
    lines += [
        "",
        "## Actual waveforms, spectra and numerical errors",
        "",
        "![Standing-wave pressure and spectra](figures/experiment_0009_waveforms.png)",
        "",
        "![Numerical field and energy errors](figures/experiment_0009_numerical.png)",
        "",
        "These are analytic standing-wave validation inputs, not QR-neuron emissions. The spectra use recorded histories, with fixed Pa amplitudes and theoretical carrier markers. Finite observation length limits frequency resolution. Temporal and spatial errors remain separate; stable bounded dynamics alone do not override a failed convergence gate.",  # noqa: E501
        "",
        "| Fixture | Grid | Maximum continuum field error | Maximum semidiscrete time error | Maximum energy drift |",  # noqa: E501
        "|---|---|---:|---:|---:|",
    ]
    for s in summaries:
        continuum = (
            f"{100 * float(s['continuum_max']):.8f}%" if s["case"].startswith("mode") else "N/A"
        )
        temporal = f"{100 * float(s['time_max']):.8f}%" if s["case"].startswith("mode") else "N/A"
        lines.append(
            f"| {s['case']} | recorded | {continuum} | {temporal} | {100 * float(s['drift']):.8f}% |"  # noqa: E501
        )
    lines += [
        "",
        "## Actual isotropic-source fields",
        "",
        "![Pressure, velocity and energy fields](figures/experiment_0009_gaussian_fields.png)",
        "",
        "Actual Gaussian-source z=11.75m slice, fixed scales throughout: pressure±80Pa, particle speed0..5e-5m/s, energy density log1e-14..3e-6J/m³. The velocity image averages incident normal faces onto pressure centres. The energy image uses symmetric half-face kinetic partition, whose integral is independently checked. Full face energy remains authoritative. Initial Gaussian fluid energy is matched to1E*, not to the standing-wave inputs' larger energies.",  # noqa: E501
        "",
        "![Gaussian pressure probes and geometric decay](figures/experiment_0009_gaussian_probes.png)",  # noqa: E501
        "",
        "Nominal probes are centre+2/4/6m; nearest pressure cells use a lowest-index tie. N48 positive-axis actual centre coordinates are13.75/15.75/17.75m with transverse11.75m (the nearest-cell sample is not an interpolated point value). Both source extent and closed walls affect observed pulses. Peak pressure is not intensity, stored energy or an integrated transmission amount. Gaussian tails at initialized cells are not validated distant arrivals. No frequency-dependent seawater attenuation curve or receiver-neuron comparison exists: those stages were gated off, not replaced by these standalone plots.",  # noqa: E501
        "",
        "## Resources, reproduction and preservation",
        "",
        f"Total observed runner wall time{sum(float(x['elapsed_seconds']) for x in q.rows(root / 'ledger.csv')):.6f}s. Standalone fields/CSV were retained; no old data were overwritten. The executable hash/compiler/source snapshot are in provenance.json, and the complete raw ledger/events/plan are packaged. The protected baseline manifest checks144 historical files, excluding only the four shared index/export files explicitly allowed to change.",  # noqa: E501
        "",
        "```sh",
        ".venv/bin/python -m pip install -r requirements-analysis.txt -r requirements-plot.txt",
        "cargo build --locked --release --bin experiment_0009",
        "cargo run --locked --release --bin experiment_0009 -- standalone results/my-0009",
        ".venv/bin/python -m analysis.experiment_0009 results/my-0009",
        ".venv/bin/python -m analysis.diagnose_experiment_0009 results/my-0009",
        ".venv/bin/python -m analysis.report_experiment_0009 results/my-0009",
        "```",
        "",
        "Use a fresh output root. Full independent verification requires the raw field archive; the compact review retains measured audit tables, source and figures but cannot reconstruct omitted fields. Source archive includes all tracked files, geometry/specification dependencies and test fixtures. No viewer is required. No viewer window or FPS measurement was performed; historical iGPU/spacing settings remain untouched.",  # noqa: E501
        "",
        "Final local tests, archive integrity/extraction, pushed SHA and exact hosted CI evidence are recorded separately in the ignored delivery-status.json after the results commit. Missing receipts mean delivery checks remain pending. Software checks do not convert scientific failures into passes.",  # noqa: E501
        "",
        "## Bounded next step",
        "",
        "A new registration would be needed to investigate any failed convergence mechanism, with separately varied time and space resolutions and the original failures retained. This run does not authorize retuning the current gates or executing the conditional neural matrix. Previous QR8 four-hop success, six-hop/participation/dual-energy failures and all earlier numerical failures remain unchanged. Principle 002 is a proposed mechanism, not an experimentally established law.",  # noqa: E501
        "",
    ]
    Path("docs/EXPERIMENT_0009_RESULTS.md").write_text("\n".join(lines))
    print(f"Rendered report and five measured figures; S1={verdict['S1']}")


if __name__ == "__main__":
    main()
