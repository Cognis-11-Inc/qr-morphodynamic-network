"""Frozen QR11 numeric-only external instruments; never installed in neurons."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as old
from analysis.audit_0011 import signature
from analysis.communication_0010 import classify
from analysis.experiment_0005 import require
from analysis.gates_0011 import compare
from analysis.package_experiment_0007 import sha
from analysis.plan_0011 import HELD, TRAIN

REPRESENTATIONS = ("SIGNED", "ENERGY", "ALL_TRACE", "INSTANT", "QR10_STYLE")
DIMENSIONS = {"SIGNED": 18, "ENERGY": 3, "ALL_TRACE": 405, "INSTANT": 128, "QR10_STYLE": 12928}


def folder(root, stage, seed, distance, module, grid="P"):
    return Path(root) / stage / f"s{seed}_d{distance}_m{module}_{grid}"


def fit(root):
    root = Path(root)
    target = root / "templates.json"
    require(
        not target.exists() and not (root / "held").exists(),
        "QR11 fit before held; no overwrite/refit",
    )
    gate = json.loads((root / "train/verification.json").read_text())
    require(gate["valid"], "QR11 calibration/training physical validity")
    models = []
    sources = {}
    for distance in (4, 6):
        for representation in REPRESENTATIONS:
            means = []
            for module in (9, 27):
                values = []
                for seed in TRAIN:
                    path = folder(root, "train", seed, distance, module)
                    value = signature(path, representation)
                    require(
                        len(value) == DIMENSIONS[representation],
                        "QR11 frozen representation dimension",
                    )
                    values.append(value)
                    sources[str(path.relative_to(root))] = sha(path / "observations.q11o")
                means.append(np.mean(values, axis=0).tolist())
            models.append(
                dict(
                    distance=distance,
                    representation=representation,
                    means=means,
                    dimension=DIMENSIONS[representation],
                )
            )
    frozen = dict(
        schema=1,
        frozen=True,
        training_seeds=TRAIN,
        held_seeds=HELD,
        primary="SIGNED",
        models=models,
        training_observation_sha256=sources,
        fit_source_sha256=sha(Path(__file__)),
    )
    target.write_text(json.dumps(frozen, indent=2) + "\n")
    (root / "TEMPLATES_SHA256.txt").write_text(f"{sha(target)}  templates.json\n")
    print("Frozen10 numeric-only models before held-out physical cases.")


def review(root):
    root = Path(root)
    digest = (root / "TEMPLATES_SHA256.txt").read_text().split()[0]
    require(sha(root / "templates.json") == digest, "QR11 frozen model integrity")
    frozen = json.loads((root / "templates.json").read_text())
    for name, value in frozen["training_observation_sha256"].items():
        require(
            sha(root / name / "observations.q11o") == value, "QR11 immutable training observations"
        )
    physical = json.loads((root / "held/verification.json").read_text())
    numerical = []
    physical_pairs = {}
    for seed in HELD:
        for distance in (4, 6):
            for module in (9, 27):
                a = folder(root, "held", seed, distance, module, "P")
                b = folder(root, "held", seed, distance, module, "F")
                values = compare(a, b)
                physical_pairs[seed, distance, module] = all(v <= 0.1 for v in values.values())
                for name, value in values.items():
                    numerical.append(
                        dict(
                            seed=seed,
                            distance=distance,
                            module=module,
                            gate=name,
                            value=value,
                            limit=0.1,
                            verdict="PASS" if value <= 0.1 else "FAIL",
                        )
                    )
    models = []
    predictions = []
    uncertainty = []
    variability = []
    for model in frozen["models"]:
        d, rep = model["distance"], model["representation"]
        correct = {"P": 0, "F": 0}
        valid = physical["valid"]
        absolute = True
        stable = True
        maximum_refinement = 0
        minimum_margin = np.inf
        for stage, seeds, grids in (("train", TRAIN, ("P",)), ("held", HELD, ("P", "F"))):
            for seed in seeds:
                vectors = {}
                for grid in grids:
                    vectors[grid] = []
                    for label, module in enumerate((9, 27)):
                        value = signature(folder(root, stage, seed, d, module, grid), rep)
                        vectors[grid].append(value)
                        prediction, distances, tie = classify(value, model["means"])
                        predictions.append(
                            dict(
                                stage=stage,
                                seed=seed,
                                distance=d,
                                representation=rep,
                                module=module,
                                grid=grid,
                                prediction=-1 if tie else (9, 27)[prediction],
                                correct=prediction == label,
                                tie=bool(tie),
                                distance9=float(distances[0]),
                                distance27=float(distances[1]),
                            )
                        )
                        if stage == "held":
                            correct[grid] += int(prediction == label)
                difference = float(np.linalg.norm(vectors["P"][0] - vectors["P"][1]))
                variation = float(
                    np.sqrt(
                        np.mean(
                            [
                                np.linalg.norm(vectors["P"][i] - np.asarray(model["means"][i])) ** 2
                                for i in (0, 1)
                            ]
                        )
                    )
                )
                variability.append(
                    dict(
                        stage=stage,
                        seed=seed,
                        distance=d,
                        representation=rep,
                        within_seed_source_difference=difference,
                        between_seed_deviation_from_training_means=variation,
                        difference_to_variation=difference / max(variation, 1e-30),
                    )
                )
                if stage == "held":
                    error = max(
                        float(np.linalg.norm(vectors["P"][i] - vectors["F"][i])) for i in (0, 1)
                    )
                    separation = min(float(np.linalg.norm(v[0] - v[1])) for v in vectors.values())
                    absolute &= separation > 1e-8
                    valid &= separation >= 5 * error
                    for i, module in enumerate((9, 27)):
                        refine = old.relative(vectors["P"][i], vectors["F"][i])
                        maximum_refinement = max(maximum_refinement, refine)
                        valid &= refine <= 0.1 and physical_pairs[seed, d, module]
                        stable &= (
                            classify(vectors["P"][i], model["means"])[0]
                            == classify(vectors["F"][i], model["means"])[0]
                        )
                    minimum_margin = min(minimum_margin, separation / max(error, 1e-30))
                    uncertainty.append(
                        dict(
                            seed=seed,
                            distance=d,
                            representation=rep,
                            separation=separation,
                            grid_discrepancy=error,
                            separation_to_uncertainty=separation / max(error, 1e-30),
                        )
                    )
        held = [
            p
            for p in predictions
            if p["stage"] == "held" and p["distance"] == d and p["representation"] == rep
        ]
        ties = any(p["tie"] for p in held)
        verdict = (
            "FAIL"
            if not absolute
            else "INDETERMINATE"
            if not valid
            else "PASS"
            if correct["P"] >= 7 and correct["F"] >= 7 and stable and not ties
            else "FAIL"
        )
        models.append(
            dict(
                distance=d,
                representation=rep,
                dimension=model["dimension"],
                primary=rep == "SIGNED",
                correct_P=correct["P"],
                correct_F=correct["F"],
                of=8,
                stable=bool(stable),
                max_feature_refinement=maximum_refinement,
                min_separation_to_uncertainty=float(minimum_margin),
                verdict=verdict,
            )
        )
    for name, data in (
        ("predictions.csv", predictions),
        ("models.csv", models),
        ("uncertainty.csv", uncertainty),
        ("variability.csv", variability),
        ("numerical.csv", numerical),
    ):
        old.csv_write(root / name, data)
    result = dict(
        schema=1,
        L2_L3_models=models,
        template_sha256=digest,
        all_predictions=len(predictions),
        primary="SIGNED",
        scope="External finite-case readout, not autonomous recognition or memory",
    )
    (root / "communication-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def retained_feature(folder):
    from analysis import io_0011 as io

    stream = io.stream(Path(folder) / "observations.q11o")
    a = stream["frames"][
        round(4 / stream["dt"]) : round(16 / stream["dt"]) + 1 : round(0.2 / stream["dt"])
    ]["nodes"][:, 1]
    value = np.stack((a["u"], a["v"]), axis=-1).ravel().copy()
    require(len(value) == 7808, "QR11 fixed retained-response dimension")
    return value


def retained_folder(root, stage, seed, distance, history, variant, grid="P"):
    return Path(root) / stage / f"s{seed}_d{distance}_h{history}_{variant}_{grid}"


def fit_retained(root):
    root = Path(root)
    require(
        not (root / "retention_templates.json").exists() and not (root / "retention_held").exists(),
        "QR11 retention freeze before held; no refit",
    )
    require(
        json.loads((root / "retention_train/verification.json").read_text())["valid"],
        "QR11 retention training physical validity",
    )
    models = []
    inputs = {}
    for distance in (4, 6):
        for variant in ("ADAPTED", "VIRGIN"):
            means = []
            for history in (9, 27):
                values = []
                for seed in TRAIN:
                    path = retained_folder(
                        root, "retention_train", seed, distance, history, variant
                    )
                    values.append(retained_feature(path))
                    inputs[str(path.relative_to(root))] = sha(path / "observations.q11o")
                means.append(np.mean(values, axis=0).tolist())
            models.append(dict(distance=distance, variant=variant, means=means))
    p = root / "retention_templates.json"
    p.write_text(
        json.dumps(
            dict(
                schema=1,
                frozen=True,
                models=models,
                dimension=7808,
                training_observation_sha256=inputs,
                fit_source_sha256=sha(Path(__file__)),
            ),
            indent=2,
        )
        + "\n"
    )
    (root / "RETENTION_TEMPLATES_SHA256.txt").write_text(f"{sha(p)}  retention_templates.json\n")


def review_retained(root):
    root = Path(root)
    digest = (root / "RETENTION_TEMPLATES_SHA256.txt").read_text().split()[0]
    require(sha(root / "retention_templates.json") == digest, "QR11 retained means immutable")
    frozen = json.loads((root / "retention_templates.json").read_text())
    for name, value in frozen["training_observation_sha256"].items():
        require(
            sha(root / name / "observations.q11o") == value,
            "QR11 retention training bytes unchanged",
        )
    receipt = json.loads((root / "retention_held/verification.json").read_text())
    predictions = []
    models = []
    causal = []
    for model in frozen["models"]:
        d, variant = model["distance"], model["variant"]
        correct = {"P": 0, "F": 0}
        valid = receipt["valid"]
        absolute = True
        stable = True
        ties = 0
        maxref = 0
        minmargin = np.inf
        for stage, seeds, grids in (
            ("retention_train", TRAIN, ("P",)),
            ("retention_held", HELD, ("P", "F")),
        ):
            for seed in seeds:
                vectors = {}
                for grid in grids:
                    vectors[grid] = []
                    for label, history in enumerate((9, 27)):
                        value = retained_feature(
                            retained_folder(root, stage, seed, d, history, variant, grid)
                        )
                        vectors[grid].append(value)
                        prediction, distances, tie = classify(value, model["means"])
                        predictions.append(
                            dict(
                                stage=stage,
                                seed=seed,
                                distance=d,
                                variant=variant,
                                history=history,
                                grid=grid,
                                prediction=-1 if tie else (9, 27)[prediction],
                                correct=prediction == label,
                                tie=bool(tie),
                                distance9=float(distances[0]),
                                distance27=float(distances[1]),
                            )
                        )
                        if stage == "retention_held":
                            correct[grid] += int(prediction == label)
                            ties += int(tie)
                if stage == "retention_held":
                    discrepancy = max(
                        float(np.linalg.norm(vectors["P"][i] - vectors["F"][i])) for i in (0, 1)
                    )
                    separation = min(float(np.linalg.norm(x[0] - x[1])) for x in vectors.values())
                    absolute &= separation > 1e-8
                    valid &= separation >= 5 * discrepancy
                    minmargin = min(minmargin, separation / max(discrepancy, 1e-30))
                    for i, history in enumerate((9, 27)):
                        ref = old.relative(vectors["P"][i], vectors["F"][i])
                        maxref = max(maxref, ref)
                        valid &= ref <= 0.1
                        stable &= (
                            classify(vectors["P"][i], model["means"])[0]
                            == classify(vectors["F"][i], model["means"])[0]
                        )
                        numerical = compare(
                            retained_folder(root, stage, seed, d, history, variant, "P"),
                            retained_folder(root, stage, seed, d, history, variant, "F"),
                        )
                        valid &= all(v <= 0.1 for v in numerical.values())
        verdict = (
            "FAIL"
            if not absolute
            else "INDETERMINATE"
            if not valid
            else "PASS"
            if correct["P"] >= 7 and correct["F"] >= 7 and stable and not ties
            else "FAIL"
        )
        models.append(
            dict(
                distance=d,
                variant=variant,
                correct_P=correct["P"],
                correct_F=correct["F"],
                of=8,
                ties=ties,
                stable=bool(stable),
                max_feature_refinement=maxref,
                min_separation_to_uncertainty=float(minmargin),
                verdict=verdict,
            )
        )
    for seed in HELD:
        for distance in (4, 6):
            for history in (9, 27):
                vectors = {}
                for grid in ("P", "F"):
                    a = retained_folder(
                        root, "retention_held", seed, distance, history, "ADAPTED", grid
                    )
                    b = retained_folder(
                        root, "retention_held", seed, distance, history, "VIRGIN", grid
                    )
                    x, y = retained_feature(a), retained_feature(b)
                    vectors[grid] = x - y
                    effect = old.relative(x, y)
                    wa = float(old.rows(a / "metrics.csv")[-1]["work"])
                    wb = float(old.rows(b / "metrics.csv")[-1]["work"])
                    causal.append(
                        dict(
                            seed=seed,
                            distance=distance,
                            history=history,
                            grid=grid,
                            relative_response_difference=effect,
                            absolute_difference=float(np.linalg.norm(x - y)),
                            source_work_relative_difference=abs(wa - wb) / abs(wb),
                        )
                    )
                delta = float(np.linalg.norm(vectors["F"]))
                uncertainty = float(np.linalg.norm(vectors["P"] - vectors["F"]))
                for row in causal[-2:]:
                    row["delta_to_uncertainty"] = delta / max(uncertainty, 1e-30)
                    row["verdict"] = (
                        "PASS"
                        if row["relative_response_difference"] >= 0.01
                        and delta > 1e-8
                        and delta >= 5 * uncertainty
                        and row["source_work_relative_difference"] <= 0.01
                        else "INDETERMINATE"
                    )
    improvement = []
    for d in (4, 6):
        a = next(m for m in models if m["distance"] == d and m["variant"] == "ADAPTED")
        b = next(m for m in models if m["distance"] == d and m["variant"] == "VIRGIN")
        passed = (
            a["verdict"] == "PASS"
            and a["correct_P"] > b["correct_P"]
            and a["correct_F"] > b["correct_F"]
        )
        improvement.append(
            dict(
                distance=d,
                verdict="PASS"
                if passed
                else "INDETERMINATE"
                if a["verdict"] == "INDETERMINATE"
                else "FAIL",
            )
        )
    for file, data in (
        ("retention_predictions.csv", predictions),
        ("retention_models.csv", models),
        ("retention_causal.csv", causal),
        ("retention_improvement.csv", improvement),
    ):
        old.csv_write(root / file, data)
    result = dict(
        schema=1,
        L5_response=causal,
        L5_models=models,
        L5_improvement=improvement,
        template_sha256=digest,
    )
    (root / "retention-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("fit", "review", "fit-retained", "review-retained"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    {
        "fit": fit,
        "review": review,
        "fit-retained": fit_retained,
        "review-retained": review_retained,
    }[a.stage](a.root)


if __name__ == "__main__":
    main()
