"""Reproduce QR7 classification from numeric-only exported observations.

Works on QUICK_REVIEW without signed whole fields. This verifies the decoder
and feature-space refinement only; it does not remeasure field energies, rules,
initial-state identity, or full-field numerical validity.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis import experiment_0007 as q7
from analysis.experiment_0005 import require, rows


def review(root):
    training = root / "train"
    result = []
    for rule in (2, 3):
        for calibrated in (True, False):
            vectors = {}
            for seed in q7.TRAIN:
                base = np.fromfile(training / f"s{seed}_CALIBRATE.f64", "<f8")
                vectors[seed] = np.array(
                    [
                        q7.vector(training, seed, rule, s, "REMOTE_ONLY")
                        - (base if calibrated else 0)
                        for s in (0, 1)
                    ]
                )
            means = q7.fit(vectors)
            suffix = "calibrated" if calibrated else "raw"
            saved = np.fromfile(training / f"template_r{rule}_{suffix}.f64", "<f8").reshape(2, 120)
            require(np.array_equal(means, saved), "independently reproduced train means")
            counts = {}
            for name in ("train", "evaluate", "refine"):
                stage = root / name
                emitted = rows(stage / "predictions.csv")
                correct = ties = total = 0
                for record in emitted:
                    if (
                        int(record["rule"]) != rule
                        or record["calibrated"] != str(calibrated).lower()
                    ):
                        continue
                    ident = record["id"]
                    seed = int(ident.split("_")[0][1:])  # External calibration lookup only.
                    raw = np.fromfile(stage / f"{ident}.f64", "<f8")
                    base = np.fromfile(stage / f"s{seed}_CALIBRATE.f64", "<f8")
                    x = raw - (base if calibrated else 0)
                    prediction, distances = q7.predict(x, means)
                    # Expected label accessed after pure numeric prediction.
                    expected = int(record["expected"])
                    stored = (
                        None if record["prediction"] == "AMBIGUOUS" else int(record["prediction"])
                    )
                    require(prediction == stored, "reproduced prediction")
                    require(
                        np.allclose(
                            distances,
                            [float(record["d0"]), float(record["d1"])],
                            rtol=1e-13,
                            atol=1e-30,
                        ),
                        "reproduced distance",
                    )
                    if "_REMOTE_ONLY" in ident:
                        correct += prediction == expected
                        ties += prediction is None
                        total += 1
                require(total == 8, "complete primary classification set")
                counts[name] = dict(correct=correct, total=total, ties=ties)
            margins = []
            for seed in q7.HELD:
                values = []
                for name in ("evaluate", "refine"):
                    stage = root / name
                    base = np.fromfile(stage / f"s{seed}_CALIBRATE.f64", "<f8")
                    values.append(
                        [
                            q7.vector(stage, seed, rule, s, "REMOTE_ONLY")
                            - (base if calibrated else 0)
                            for s in (0, 1)
                        ]
                    )
                separation = float(np.linalg.norm(values[1][1] - values[1][0]))
                error = max(float(np.linalg.norm(values[0][s] - values[1][s])) for s in (0, 1))
                relative = max(q7.relative(values[0][s], values[1][s]) for s in (0, 1))
                margins.append(
                    dict(
                        seed=seed,
                        separation=separation,
                        max_error=error,
                        max_relative_error=relative,
                        pass_gate=separation > 1e-10
                        and separation >= 5 * error
                        and relative <= 0.05,
                    )
                )
            result.append(dict(rule=rule, calibrated=calibrated, counts=counts, margins=margins))
    return dict(
        scope="classification and feature refinement only; whole-field gates not remeasured",
        models=result,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(review(args.root), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
