"""Recorded QR13 CPU inference costs; no model selection or research-efficiency claim."""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from analysis.dataset_0013 import arrays, save
from analysis.learn_0013 import forecast
from analysis.models_0013 import setup
from analysis.structure_0013 import physical_predict


def benchmark(root):
    root = Path(root)
    setup()
    records = json.loads((root / "training.json").read_text()) + json.loads(
        (root / "baselines.json").read_text()
    )
    case = next(
        r
        for r in json.loads((root / "prospective-inventory.json").read_text())
        if r["id"] == "QR13__s431_FIXED_P"
    )
    result = []
    for r in records:
        data = arrays(root, case, r["observer"], r["morphology"])

        def run(record=r, features=data):
            return (
                physical_predict(root, case, record["observer"])
                if record["kind"] == "physical"
                else forecast(root, record, features)
            )

        run()
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            run()
            timings.append(time.perf_counter() - start)
        result.append(
            dict(
                model=r["id"],
                model_artifact_bytes=(root / r["file"]).stat().st_size if "file" in r else 0,
                individual_neural_fit_seconds=r.get("seconds"),
                origins=len(data["y"]),
                horizons=3,
                seconds=timings,
                median_seconds=float(np.median(timings)),
                scope="CPU end-to-end forecast includes normalization/model loading; "
                "excludes extraction and output compression",
            )
        )
    save(
        root / "inference-costs.json",
        dict(
            measurements=result,
            limitation="Baseline uses frozen dense coefficients, not optimized low-rank factors. "
            "These timings are not a fair algorithmic speed superiority "
            "or hypothesis-selection study. G6 remains NOT RUN.",
        ),
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(f"{len(benchmark(a.root))} models benchmarked")


if __name__ == "__main__":
    main()
