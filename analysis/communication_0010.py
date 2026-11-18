"""Frozen numeric-only QR10 calibration templates, held-out readout and interference."""

import argparse
import json
import math
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as old
from analysis import experiment_0010 as fluid
from analysis.audit_coupling_0010 import history, neural
from analysis.experiment_0005 import require
from analysis.package_experiment_0007 import sha


def case_name(seed, module, band, distance, n=48, dt=0.05, control="FLUID"):
    return f"s{seed}_m{module}_b{band}_d{distance}_n{n}_dt{dt}_{control}"


def feature(folder):
    """101 actual remote times,64 modules,u/v, no metadata in the vector."""
    return history(folder)[40:241:2].ravel()


def training_folder(root, seed, module, band, distance):
    name = case_name(seed, module, band, distance)
    return (
        (root.parent / "pilot" / name)
        if (seed, band, distance) == (211, 0, 2)
        else root / "train" / name
    )


def fit(root):
    destination = root / "templates.json"
    require(not destination.exists(), "refuse template overwrite/refit")
    receipt = json.loads((root / "train/verification.json").read_text())
    require(
        receipt["verdicts"]["C3"] == receipt["verdicts"]["C7"] == "PASS",
        "calibration numerical accounting and reliability",
    )
    require(not (root / "evaluate").exists(), "no held-out outcomes before freeze")
    models = []
    sources = {}
    for band in range(3):
        for distance in (2, 4, 6):
            means = []
            for module in (9, 27):
                cases = [training_folder(root, seed, module, band, distance) for seed in (211, 223)]
                for folder in cases:
                    sources[str(folder.relative_to(root.parent))] = sha(folder / "history.csv")
                means.append(np.mean([feature(folder) for folder in cases], axis=0).tolist())
            models.append(dict(band=band, distance=distance, class_modules=[9, 27], means=means))
    result = dict(
        schema=1,
        frozen=True,
        decoders=9,
        class_vectors=18,
        dimension=12928,
        method="Unscaled Euclidean nearest class mean, ties incorrect",
        models=models,
        training_history_sha256=sources,
        verifier_sha256=sha(Path(__file__)),
    )
    destination.write_text(json.dumps(result, indent=2) + "\n")
    (root / "TEMPLATES_SHA256.txt").write_text(f"{sha(destination)}  templates.json\n")
    print("Frozen9 decoders/18 class vectors from36 calibration cases (2 pilot reuses).")


def classify(vector, means):
    distances = np.linalg.norm(np.asarray(means) - vector[None, :], axis=1)
    tie = abs(distances[0] - distances[1]) <= 1e-12 * max(*distances, 1e-30)
    return (-1 if tie else int(np.argmin(distances))), distances, tie


def review(root):
    receipt = (root / "TEMPLATES_SHA256.txt").read_text().split()[0]
    require(receipt == sha(root / "templates.json"), "frozen template integrity")
    frozen = json.loads((root / "templates.json").read_text())
    for name, digest in frozen["training_history_sha256"].items():
        require(sha(root.parent / name / "history.csv") == digest, "unchanged calibration bytes")
    calibration_predictions = []
    for model in frozen["models"]:
        for seed in (211, 223):
            for label, module in enumerate((9, 27)):
                folder = training_folder(root, seed, module, model["band"], model["distance"])
                prediction, distances, tie = classify(feature(folder), model["means"])
                calibration_predictions.append(
                    dict(
                        band=model["band"],
                        distance=model["distance"],
                        seed=seed,
                        module=module,
                        prediction_module=-1 if tie else (9, 27)[prediction],
                        tie=bool(tie),
                        correct=prediction == label,
                        distance9=float(distances[0]),
                        distance27=float(distances[1]),
                    )
                )
    old.csv_write(root / "calibration_predictions.csv", calibration_predictions)
    numerical = json.loads((root / "evaluate/verification.json").read_text())
    numeric_valid = all(numerical["verdicts"][q] == "PASS" for q in ("C3", "C7"))
    predictions = []
    decoders = []
    uncertainties = []
    responses = []
    feature_valid = {}
    for model in frozen["models"]:
        band, distance = model["band"], model["distance"]
        correct = {"primary": 0, "fine": 0}
        valid = True
        floor = True
        stable = True
        max_refinement = 0
        min_ratio = math.inf
        for seed in (227, 229):
            vectors = {}
            for grid, n, dt in (("primary", 48, 0.05), ("fine", 96, 0.025)):
                vectors[grid] = []
                for label, module in enumerate((9, 27)):
                    folder = root / "evaluate" / case_name(seed, module, band, distance, n, dt)
                    vector = feature(folder)
                    vectors[grid].append(vector)
                    prediction, dists, tie = classify(vector, model["means"])
                    correct[grid] += int(prediction == label)
                    predictions.append(
                        dict(
                            band=band,
                            distance=distance,
                            seed=seed,
                            module=module,
                            grid=grid,
                            prediction_module=-1 if tie else (9, 27)[prediction],
                            tie=bool(tie),
                            correct=prediction == label,
                            distance9=float(dists[0]),
                            distance27=float(dists[1]),
                        )
                    )
                    rows = old.rows(folder / "metrics.csv")
                    work = float(rows[-1]["work"])
                    emitted = float(rows[-1]["source_positive"])
                    energy = np.array([float(r["receiver_energy"]) for r in rows])
                    peak = float(energy.max())
                    arrival = next(
                        (
                            int(r["tick"]) * dt
                            for r in rows
                            if float(r["receiver_energy"]) > 1e-10 * max(work, 1e-30)
                        ),
                        None,
                    )
                    responses.append(
                        dict(
                            band=band,
                            distance=distance,
                            seed=seed,
                            module=module,
                            grid=grid,
                            work=work,
                            emitted_positive=emitted,
                            source_backflow=float(rows[-1]["source_backflow"]),
                            receiver_peak=peak,
                            receiver_per_work=peak / max(work, 1e-30),
                            receiver_per_emitted=peak / max(emitted, 1e-30),
                            arrival=arrival,
                            peak_time=int(rows[int(energy.argmax())]["tick"]) * dt,
                        )
                    )
            errors = [
                float(np.linalg.norm(vectors["primary"][i] - vectors["fine"][i])) for i in (0, 1)
            ]
            separations = {grid: float(np.linalg.norm(v[0] - v[1])) for grid, v in vectors.items()}
            maxerr = max(errors)
            for label in (0, 1):
                refinement = old.relative(vectors["primary"][label], vectors["fine"][label])
                max_refinement = max(max_refinement, refinement)
                valid &= refinement <= 0.1
                feature_valid[band, distance, seed, (9, 27)[label]] = refinement <= 0.1
                pa = classify(vectors["primary"][label], model["means"])[0]
                pb = classify(vectors["fine"][label], model["means"])[0]
                stable &= pa == pb
            for grid, separation in separations.items():
                floor &= separation > 1e-8
                valid &= separation >= 5 * maxerr
                min_ratio = min(min_ratio, separation / max(maxerr, 1e-30))
                uncertainties.append(
                    dict(
                        band=band,
                        distance=distance,
                        seed=seed,
                        grid=grid,
                        separation=separation,
                        maximum_grid_discrepancy=maxerr,
                        separation_to_discrepancy=separation / max(maxerr, 1e-30),
                    )
                )
        verdict = (
            "FAIL"
            if not floor
            else "INDETERMINATE"
            if not valid or not numeric_valid
            else "PASS"
            if correct["primary"] == correct["fine"] == 4 and stable
            else "FAIL"
        )
        decoders.append(
            dict(
                band=band,
                distance=distance,
                primary_correct=correct["primary"],
                fine_correct=correct["fine"],
                of=4,
                predictions_stable=bool(stable),
                maximum_feature_refinement=max_refinement,
                minimum_separation_to_uncertainty=min_ratio,
                verdict=verdict,
            )
        )
    for name, records in (
        ("predictions.csv", predictions),
        ("decoders.csv", decoders),
        ("uncertainty.csv", uncertainties),
        ("responses.csv", responses),
    ):
        old.csv_write(root / name, records)
    band_comparisons = []
    lookup = {(r["band"], r["distance"], r["seed"], r["module"], r["grid"]): r for r in responses}
    level_b = (
        json.loads((root.parent / "numerical/verification.json").read_text())["level_B"] == "PASS"
    )
    for distance in (2, 4, 6):
        for seed in (227, 229):
            for module in (9, 27):
                for a, b in ((0, 1), (0, 2), (1, 2)):
                    ap = lookup[a, distance, seed, module, "primary"]["receiver_per_emitted"]
                    af = lookup[a, distance, seed, module, "fine"]["receiver_per_emitted"]
                    bp = lookup[b, distance, seed, module, "primary"]["receiver_per_emitted"]
                    bf = lookup[b, distance, seed, module, "fine"]["receiver_per_emitted"]
                    discrepancy = abs(ap - af) + abs(bp - bf)
                    difference = abs(af - bf)
                    # Registered difference criterion; no added ranking assumption.
                    supported = (
                        level_b
                        and numeric_valid
                        and feature_valid[a, distance, seed, module]
                        and feature_valid[b, distance, seed, module]
                        and difference > 5 * discrepancy
                    )
                    band_comparisons.append(
                        dict(
                            distance=distance,
                            seed=seed,
                            module=module,
                            band_a=a,
                            band_b=b,
                            fine_a=af,
                            fine_b=bf,
                            absolute_difference=difference,
                            grid_uncertainty=discrepancy,
                            verdict="PASS" if supported else "INDETERMINATE",
                        )
                    )
    old.csv_write(root / "band_comparisons.csv", band_comparisons)
    # All signed spectra retained, no presumed ranking or material absorption interpretation.
    spectra = []
    for r in responses:
        n, dt = (48, 0.05) if r["grid"] == "primary" else (96, 0.025)
        folder = (
            root / "evaluate" / case_name(r["seed"], r["module"], r["band"], r["distance"], n, dt)
        )
        p = np.array([float(x["q"]) for x in old.rows(folder / "probes.csv")])
        z = np.fft.rfft(p) * 0.1
        for frequency, value in zip(np.fft.rfftfreq(len(p), 0.1), z, strict=True):
            spectra.append(
                dict(
                    band=r["band"],
                    distance=r["distance"],
                    seed=r["seed"],
                    module=r["module"],
                    grid=r["grid"],
                    normalized_frequency=float(frequency),
                    pressure_real=float(value.real),
                    pressure_imag=float(value.imag),
                )
            )
    old.csv_write(root / "signed_spectra.csv", spectra)
    result = dict(
        schema=1,
        C4=decoders,
        held_out_predictions=len(predictions),
        calibration_predictions=len(calibration_predictions),
        C5=band_comparisons,
        all_incorrect_and_ties_retained=True,
        templates_sha256=receipt,
        scope="Finite stationary discrimination; no learning, memory or bitrate claim",
    )
    (root / "communication-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def interference(root):
    numerical = json.loads((root / "interference/verification.json").read_text())
    valid = all(numerical["verdicts"][q] == "PASS" for q in ("C3", "C7"))
    observations = []
    for n, dt in ((48, 0.05), (96, 0.025)):
        folders = {
            arm: root / "interference" / case_name(211, 9, 0, 4, n, dt, arm)
            for arm in ("IA", "IB", "IAB+", "IAB-")
        }
        histories = {arm: history(folder) for arm, folder in folders.items()}
        for sign, arm in ((1, "IAB+"), (-1, "IAB-")):
            expected = histories["IA"] + sign * histories["IB"]
            residual = old.relative(histories[arm], expected)
            observations.append(
                dict(
                    n=n,
                    dt=dt,
                    time="every.1",
                    arm=arm,
                    quantity="remote_signed_history",
                    residual=residual,
                    verdict="PASS" if valid and residual <= 1e-10 else "FAIL",
                )
            )
            for time in (0, 12, 24):
                tick = round(time / dt)
                fields = {
                    a: fluid.decode(f / f"{tick:06}.q10")["fields"] for a, f in folders.items()
                }
                expected = fields["IA"] + sign * fields["IB"]
                residual = old.relative(fields[arm], expected)
                e = {a: fluid.energy(f, 24 / n) for a, f in fields.items()}
                # Cross term is signed, and is not interpreted as lost energy.
                cross = e[arm] - e["IA"] - e["IB"]
                _, ua, va = neural(folders["IA"] / f"{tick:06}.neuron.csv")
                _, ub, vb = neural(folders["IB"] / f"{tick:06}.neuron.csv")
                _, uc, vc = neural(folders[arm] / f"{tick:06}.neuron.csv")
                nr = old.relative(np.stack((uc, vc)), np.stack((ua + sign * ub, va + sign * vb)))
                observations.append(
                    dict(
                        n=n,
                        dt=dt,
                        time=str(time),
                        arm=arm,
                        quantity="full_signed_fluid_and_neurons",
                        residual=max(residual, nr),
                        verdict="PASS" if valid and max(residual, nr) <= 1e-10 else "FAIL",
                        fluid_cross_energy=cross,
                    )
                )
    import csv

    keys = list(dict.fromkeys(k for r in observations for k in r))
    with (root / "interference.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(observations)
    result = dict(
        C6="PASS" if all(r["verdict"] == "PASS" for r in observations) else "FAIL",
        observations=observations,
    )
    (root / "interference-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "review", "interference"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"fit": fit, "review": review, "interference": interference}[args.stage](args.root)


if __name__ == "__main__":
    main()
