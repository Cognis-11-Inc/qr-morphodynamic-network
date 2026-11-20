"""Descriptive stability of frozen QR13 external forecasts; no new success threshold."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis.dataset_0013 import save


def review(root):
    root = Path(root)
    records = json.loads((root / "training.json").read_text()) + json.loads(
        (root / "baselines.json").read_text()
    )
    result = []
    for model in records:
        finite = negative = energy_count = 0
        peak = 0.0
        percase = []
        for path in sorted(
            (root / "predictions_prospective_test").glob("*___" + model["id"] + ".npz")
        ):
            with np.load(path) as a:
                prediction = (
                    a["prediction"]
                    .reshape(-1, 3, 130 if model["observer"] == "local" else 520)
                    .reshape(-1, 3, 1 if model["observer"] == "local" else 4, 130)
                )
            finite += int(np.isfinite(prediction).all())
            negative += int(np.count_nonzero(prediction[..., 129] < 0))
            energy_count += prediction[..., 129].size
            value = float(abs(prediction[..., :128]).max())
            peak = max(peak, value)
            percase.append(
                dict(
                    file=path.name,
                    peak_abs_signed_state=value,
                    negative_energy_predictions=int(np.count_nonzero(prediction[..., 129] < 0)),
                )
            )
        result.append(
            dict(
                model=model["id"],
                finite_cases=finite,
                cases=len(percase),
                negative_energy_predictions=negative,
                energy_predictions=energy_count,
                peak_abs_signed_state=peak,
                per_case=percase,
            )
        )
    save(
        root / "prediction-stability.json",
        dict(
            records=result,
            scope="Fixed finite horizons, not long-time stability or a physical law. "
            "Negative learned energy is a prediction defect, never an intervention. "
            "Recursive accumulation is reported separately.",
        ),
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    review(a.root)


if __name__ == "__main__":
    main()
