"""Independent QR13 origin/alignment/leakage and frozen-prediction verification."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis import io_0012
from analysis.dataset_0013 import arrays, partition, save, sha
from analysis.experiment_0005 import require
from analysis.experiment_0009 import rows


def audit_dataset(root):
    root = Path(root)
    inventory = json.loads((root / "inventory.json").read_text())
    if (root / "prospective-inventory.json").exists():
        inventory += json.loads((root / "prospective-inventory.json").read_text())
    results = []
    families = {}
    for r in inventory:
        folder = Path(r["source"])
        if not folder.exists():
            # Portable archives keep the repository-relative source path.
            parts = folder.parts
            index = parts.index("results")
            folder = Path(*parts[index:])
        metadata = rows(folder / "metadata.csv")[0]
        require(metadata == r["metadata"], "QR13 inventory actual metadata binding")
        require(partition(int(metadata["seed"])) == r["partition"], "QR13 family partition")
        families.setdefault(r["family"], set()).add(r["partition"])
        path = root / "data" / (r["id"] + ".npz")
        require(sha(path) == r["data_sha256"], "QR13 immutable compact dataset")
        s = io_0012.stream(folder)
        raw = s["frames"][:: round(0.2 / s["dt"])]
        with np.load(path) as a:
            for field in ("u", "v", "packet", "z", "palette"):
                require(
                    np.array_equal(a[field], raw["nodes"][field]), "QR13 exact raw/compact " + field
                )
            require(np.array_equal(a["ticks"], raw["tick"]), "QR13 unaltered raw ticks")
            require(
                np.allclose(a["time"], raw["tick"] * s["dt"], rtol=0, atol=1e-13), "QR13 time units"
            )
            for node in range(s["count"]):
                require(
                    np.all(raw["nodes"]["age"][:, node] == raw["tick"]),
                    "QR13 independently ordered local ages",
                )
            if metadata["checkpoint"]:
                ancestor = Path(metadata["checkpoint"])
                if not ancestor.exists():
                    parts = ancestor.parts
                    ancestor = Path(*parts[parts.index("results") :])
                require(
                    (folder / "branch-before.q12").read_bytes() == ancestor.read_bytes(),
                    "QR13 actual causal ancestry",
                )
            if r["model_eligible"]:
                for observer in ("local", "global"):
                    features = arrays(root, r, observer, True)
                    origins = np.arange(2, len(raw) - 10)
                    expected_times = a["time"][origins]
                    require(
                        np.array_equal(
                            features["time"],
                            expected_times
                            if observer == "global"
                            else np.repeat(expected_times, 4),
                        ),
                        "QR13 forecast origins",
                    )
                    expected = np.concatenate(
                        (a["u"], a["v"], a["packet"][..., :1], a["energy"][..., None]), axis=-1
                    )
                    target = np.stack([expected[origins + step] for step in (1, 5, 10)], axis=1)
                    target = (
                        target.reshape(len(origins), 3, -1)
                        if observer == "global"
                        else target.transpose(0, 2, 1, 3).reshape(-1, 3, 130)
                    )
                    require(
                        np.array_equal(target, features["y"]), "QR13 direct physical horizon labels"
                    )
                    require(np.isfinite(features["x"]).all(), "QR13 finite causal inputs")
        if not r["protocol_valid"] or not r["numerical_valid"]:
            require(not r["model_eligible"], "QR13 invalid controls excluded")
        results.append(
            dict(id=r["id"], valid=True, observations=r["observations"], partition=r["partition"])
        )
    require(all(len(p) == 1 for p in families.values()), "QR13 ancestry never crosses partitions")
    result = dict(
        G1="PASS",
        executions=len(results),
        families={k: list(v) for k, v in families.items()},
        checks=results,
        interpretation="verified origin/alignment; no statistical independence from timestamps",
        inventory_sha256=sha(root / "inventory.json"),
    )
    save(root / "dataset-verification.json", result)
    return result


def audit_predictions(root, partition):
    root = Path(root)
    records = json.loads((root / "training.json").read_text())
    records += json.loads((root / "baselines.json").read_text())
    inventory = json.loads((root / "inventory.json").read_text())
    if (root / "prospective-inventory.json").exists():
        inventory += json.loads((root / "prospective-inventory.json").read_text())
    bycase = {r["id"]: r for r in inventory}
    bymodel = {r["id"]: r for r in records}
    checked = 0
    for row in rows(root / (partition + "-metrics.csv")):
        if row["stratum"] not in ("all", "event_crossing", "ordinary", "accepted_event"):
            continue
        record = bymodel[row["model"]]
        case = bycase[row["case"]]
        data = arrays(root, case, record["observer"], record["morphology"])
        path = root / ("predictions_" + partition) / (case["id"] + "___" + record["id"] + ".npz")
        with np.load(path) as p:
            prediction = p["prediction"]
            require(np.array_equal(p["time"], data["time"]), "QR13 prediction/origin alignment")
        with np.load(root / record["normalization"]) as n:
            scale = n["scale"]
        error = ((prediction - data["y"]) / scale) ** 2
        if record["observer"] == "local":
            error = error.reshape(-1, 4, 3, 130).transpose(0, 2, 1, 3)
            crossing, accepted = data["crossing"][::4], data["accepted"][::4]
        else:
            error = error.reshape(-1, 3, 4, 130)
            crossing, accepted = data["crossing"], data["accepted"]
        mask = {
            "all": None,
            "event_crossing": crossing,
            "ordinary": ~crossing,
            "accepted_event": accepted,
        }[row["stratum"]]
        if mask is not None:
            error = error[mask]
        if error.size:
            measured = float(error[..., :128].mean())
            claimed = float(row["uv_loss"])
            require(
                abs(measured - claimed) <= 1e-12 * max(abs(measured), 1),
                "QR13 independently reconstructed forecast loss",
            )
        else:
            require(row["uv_loss"] in ("", "None"), "QR13 undefined strata remain undefined")
        checked += 1
    result = dict(partition=partition, checked_losses=checked, valid=True)
    save(root / (partition + "-independent-metrics-audit.json"), result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--predictions", choices=("retrospective_test", "prospective_test"))
    a = p.parse_args()
    print(
        json.dumps(
            audit_predictions(a.root, a.predictions) if a.predictions else audit_dataset(a.root),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
