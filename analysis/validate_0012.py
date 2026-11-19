"""Fresh portable reconstruction of all executed QR12 stages and declared predictions."""

import argparse
import json
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from analysis.audit_0012 import stage
from analysis.causal_0012 import review as causal
from analysis.collective_0012 import review as collective
from analysis.composition_0012 import mathematical_tests, predict_case, review
from analysis.experiment_0005 import require
from analysis.experiment_0009 import relative
from analysis.gates_0012 import a, b
from analysis.report_0012 import coverage


def validate(root, jobs=4):
    root = Path(root)
    stages = [root / s for s in "abcde" if (root / s / "ledger.csv").exists()]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        tasks = {s.name: pool.submit(stage, s, True) for s in stages}
        results = {key: job.result() for key, job in tasks.items()}
    require(all(r["valid"] for r in results.values()), "QR12 fresh physical audits valid")
    results["A"] = a(root)
    if (root / "b/ledger.csv").exists():
        results["B"] = b(root)
    if (root / "c/ledger.csv").exists():
        results["C"] = causal(root)
    if (root / "d/ledger.csv").exists():
        results["D"] = collective(root)
    results["formal"] = mathematical_tests(root)
    if (root / "e/ledger.csv").exists():
        frozen = json.loads((root / "predictions/freeze.json").read_text())
        errors = []
        with tempfile.TemporaryDirectory(prefix="qr12-prediction-replay-") as temp:
            for original in frozen["predictions"]:
                prediction = predict_case(original["inputs"], Path(temp))
                for name in prediction["files"]:
                    old = np.load(root / "predictions" / name)
                    new = np.load(Path(temp) / name)
                    for key in ("fields", "nodes"):
                        if key == "fields":
                            error = relative(new[key], old[key])
                        else:
                            error = max(
                                relative(new[key][field], old[key][field])
                                for field in ("u", "v", "z", "loss", "packet")
                            )
                        require(error <= 1e-10, "QR12 independent prediction re-execution agrees")
                        errors.append(dict(file=name, component=key, error=error))
        results["prediction_replay"] = errors
        results["E"] = review(root)
    results["coverage"] = coverage(root)
    (root / "portable-validation.json").write_text(json.dumps(results, indent=2) + "\n")
    print("Fresh QR12 physical, event, fork, collective and compositional reconstruction complete.")
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--jobs", type=int, choices=range(1, 5), default=4)
    a = p.parse_args()
    validate(a.root, a.jobs)


if __name__ == "__main__":
    main()
