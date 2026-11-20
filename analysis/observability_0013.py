"""Post-outcome identical-input/different-target diagnostic, never a model repair."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis.dataset_0013 import TEST_SEEDS, arrays, save
from analysis.experiment_0009 import csv_write, rows


def review(root):
    root = Path(root)
    inventory = json.loads((root / "prospective-inventory.json").read_text())
    byid = {r["id"]: r for r in inventory}
    result = []
    with np.load(root / "models/global_1_normalization.npz") as norm:
        scale = norm["scale"].reshape(4, 130)[..., :128].copy()
    for seed in TEST_SEEDS:
        for grid in "PF":
            fixed = arrays(root, byid[f"QR13__s{seed}_FIXED_{grid}"], "global", True)
            adaptive = arrays(root, byid[f"QR13__s{seed}_ADAPTIVE_{grid}"], "global", True)
            identical = (fixed["x"] == adaptive["x"]).all(axis=(1, 2)) & (
                fixed["palette"] == adaptive["palette"]
            ).all(axis=1)
            delta = (fixed["y"] - adaptive["y"]).reshape(-1, 3, 4, 130)[..., :128]
            conflicting = identical[:, None] & np.any(delta != 0, axis=(2, 3))
            # For equal paired labels a,b at identical x, best squared-loss prediction
            # is (a+b)/2 and minimum policy-average squared error is (a-b)^2/4.
            floor = float(np.mean((delta / scale) ** 2 * identical[:, None, None, None] / 4))
            times = fixed["time"][np.any(conflicting, axis=1)]
            result.append(
                dict(
                    seed=seed,
                    grid=grid,
                    valid_family=all(r["numerical_valid"] for r in inventory if r["seed"] == seed),
                    origins=len(identical),
                    identical_input_origins=int(identical.sum()),
                    conflicting_horizon_labels=int(conflicting.sum()),
                    first_conflicting_origin=float(times.min()) if len(times) else None,
                    last_conflicting_origin=float(times.max()) if len(times) else None,
                    normalized_uv_mse_lower_bound=floor,
                )
            )
    csv_write(root / "post-outcome-observation-collisions.csv", result)
    baseline = json.loads((root / "selection.json").read_text())["baseline"]
    metric = rows(root / "prospective_test-metrics.csv")
    values = [
        r["normalized_uv_mse_lower_bound"] for r in result if r["grid"] == "P" and r["valid_family"]
    ]
    losses = [
        float(r["uv_loss"])
        for r in metric
        if r["model"] == baseline
        and r["grid"] == "48"
        and r["stratum"] == "all"
        and any(v["valid_family"] and int(r["seed"]) == v["seed"] for v in result)
    ]
    save(
        root / "post-outcome-observability.json",
        dict(
            analysis_status="POST-OUTCOME DESCRIPTIVE; not a development-selected G5 discovery",
            proof="At identical x and equally weighted labels a,b, "
            "the conditional-mean minimum MSE is (a-b)^2/4.",
            valid_family_mean_normalized_uv_floor=float(np.mean(values)),
            fraction_of_selected_baseline_error=float(np.mean(values) / np.mean(losses)),
            policy_omitted_by_registered_observer=True,
            does_not_change_models_or_registered_gates=True,
            rows=result,
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
