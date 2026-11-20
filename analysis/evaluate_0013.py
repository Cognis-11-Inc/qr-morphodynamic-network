"""Frozen QR13 forecasts, paired family uncertainty and prospective gate reconstruction."""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from analysis.dataset_0013 import arrays, save
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write
from analysis.learn_0013 import forecast
from analysis.models_0013 import setup
from analysis.structure_0013 import physical_predict


def paired_test(reference, learned):
    """Exact paired sign randomization and family bootstrap; no timestamp p-values."""
    a, b = np.asarray(reference, float), np.asarray(learned, float)
    require(a.shape == b.shape and a.ndim == 1 and len(a) > 0, "QR13 paired family arrays")
    d = a - b
    n = len(a)
    signs = 2 * ((np.arange(2**n)[:, None] >> np.arange(n)) & 1) - 1
    p = float(np.mean((signs @ d / n) >= d.mean() - 1e-15))
    rng = np.random.default_rng(1300)
    indices = rng.integers(0, n, size=(10000, n))
    improvement = (a[indices].mean(1) - b[indices].mean(1)) / np.maximum(a[indices].mean(1), 1e-30)
    return dict(
        families=n,
        reference=a.tolist(),
        learned=b.tolist(),
        relative_improvement=float((a.mean() - b.mean()) / max(a.mean(), 1e-30)),
        p_one_sided=p,
        bootstrap95=np.quantile(improvement, [0.025, 0.975]).tolist(),
    )


def summary(pred, target, scale, mask=None):
    err = (pred - target).reshape(len(pred), 3, 4, 130)
    norm = err / scale.reshape(1, 1, 4, 130)
    if mask is not None:
        err, norm = err[mask], norm[mask]
    if not err.size:
        return dict(uv_loss=None, rmse=None, pressure_loss=None, energy_loss=None)
    return dict(
        uv_loss=float(np.mean(norm[..., :128] ** 2)),
        rmse=float(np.sqrt(np.mean(err[..., :128] ** 2))),
        pressure_loss=float(np.mean(norm[..., 128] ** 2)),
        energy_loss=float(np.mean(norm[..., 129] ** 2)),
    )


def recursive(root, record, data):
    current = {k: v.copy() for k, v in data.items()}
    for _ in range(10):
        out, _ = forecast(root, record, current)
        value = out[:, 0]
        old = current["x"][:, -1].copy()
        width = 159
        for node in range(4):
            begin = node * width
            y = value[:, node * 130 : (node + 1) * 130]
            old[:, begin : begin + 128] = y[:, :128]
            old[:, begin + 128] = y[:, 128]
            old[:, begin + 135] = y[:, 129]
            old[:, begin + 158] += 0.2
        current["x"] = np.concatenate((current["x"][:, 1:], old[:, None]), axis=1)
        current["current"] = value
    return value


def evaluate(root, partition, force=False):
    root = Path(root)
    setup()
    inv = json.loads((root / "inventory.json").read_text())
    if (root / "prospective-inventory.json").exists():
        inv += json.loads((root / "prospective-inventory.json").read_text())
    selection = json.loads((root / "selection.json").read_text())
    records = json.loads((root / "training.json").read_text()) + json.loads(
        (root / "baselines.json").read_text()
    )
    dest = root / ("predictions_" + partition)
    dest.mkdir(exist_ok=True)
    metrics = []
    begun = time.perf_counter()
    for case in inv:
        if case["partition"] != partition or not (
            case["model_eligible"] or case.get("prediction_eligible", False)
        ):
            continue
        for record in records:
            data = arrays(root, case, record["observer"], record["morphology"])
            path = dest / (case["id"] + "___" + record["id"] + ".npz")
            with np.load(root / record["normalization"]) as norm:
                scale = norm["scale"].copy()
            if path.exists() and not force:
                with np.load(path) as old:
                    pred = old["prediction"].copy()
            elif record["kind"] == "physical":
                pred = physical_predict(root, case, record["observer"])
                np.savez_compressed(path, prediction=pred, time=data["time"], node=data["node"])
            else:
                pred, _ = forecast(root, record, data)
                np.savez_compressed(path, prediction=pred, time=data["time"], node=data["node"])
            require(np.isfinite(pred).all(), "QR13 finite external prediction")
            if record["observer"] == "local":
                pred = pred.reshape(-1, 4, 3, 130).transpose(0, 2, 1, 3).reshape(-1, 3, 520)
                target = data["y"].reshape(-1, 4, 3, 130).transpose(0, 2, 1, 3).reshape(-1, 3, 520)
                scale = np.tile(scale, 4)
                crossing = data["crossing"][::4]
                accepted = data["accepted"][::4]
            else:
                target = data["y"]
                crossing = data["crossing"]
                accepted = data["accepted"]
            details = []
            for label, mask in (
                ("all", None),
                ("event_crossing", crossing),
                ("ordinary", ~crossing),
                ("accepted_event", accepted),
            ):
                details.append(dict(stratum=label, **summary(pred, target, scale, mask)))
            errors = (pred - target).reshape(-1, 3, 4, 130)
            for horizon in range(3):
                for node in range(4):
                    for block, a, b in (
                        ("u", 0, 64),
                        ("v", 64, 128),
                        ("pressure", 128, 129),
                        ("energy", 129, 130),
                    ):
                        e = errors[:, horizon, node, a:b]
                        truth = target.reshape(-1, 3, 4, 130)[:, horizon, node, a:b]
                        details.append(
                            dict(
                                stratum=f"h{(0.2, 1.0, 2.0)[horizon]}_N{node}_{block}",
                                uv_loss=None,
                                rmse=float(np.sqrt(np.mean(e**2))),
                                relative_l2=float(
                                    np.linalg.norm(e) / max(float(np.linalg.norm(truth)), 1e-30)
                                ),
                            )
                        )
            for row in details:
                metrics.append(
                    dict(
                        case=case["id"],
                        model=record["id"],
                        seed=case["seed"],
                        grid=case["metadata"]["n"],
                        dt=case["metadata"]["dt"],
                        policy=case["metadata"]["policy"],
                        **row,
                    )
                )
            if (
                record["id"] in (selection["primary"], selection["baseline"])
                and record["kind"] != "physical"
            ) and record["observer"] == "global":
                roll = recursive(root, record, data)
                np.savez_compressed(
                    dest / (case["id"] + "___" + record["id"] + "_recursive.npz"),
                    prediction=roll,
                    time=data["time"],
                )
                diff = roll - data["y"][:, 2]
                metrics.append(
                    dict(
                        case=case["id"],
                        model=record["id"],
                        seed=case["seed"],
                        grid=case["metadata"]["n"],
                        dt=case["metadata"]["dt"],
                        policy=case["metadata"]["policy"],
                        stratum="recursive_2.0",
                        uv_loss=float(
                            np.mean(
                                (
                                    diff.reshape(-1, 4, 130)[..., :128]
                                    / scale.reshape(4, 130)[..., :128]
                                )
                                ** 2
                            )
                        ),
                        rmse=float(np.sqrt(np.mean(diff**2))),
                    )
                )
        print("QR13 evaluated", partition, case["id"], flush=True)
    require(metrics, "QR13 actual held observations")
    # Sparse block rows have different diagnostic columns; use a common explicit schema.
    keys = (
        "case",
        "model",
        "seed",
        "grid",
        "dt",
        "policy",
        "stratum",
        "uv_loss",
        "rmse",
        "pressure_loss",
        "energy_loss",
        "relative_l2",
    )
    csv_write(root / (partition + "-metrics.csv"), [{k: r.get(k) for k in keys} for r in metrics])
    save(
        root / (partition + "-evaluation.json"),
        dict(
            seconds=time.perf_counter() - begun,
            rows=len(metrics),
            cases=sorted({r["case"] for r in metrics}),
            models=[r["id"] for r in records],
        ),
    )
    return metrics


def gates(root):
    from analysis.experiment_0009 import rows

    root = Path(root)
    m = rows(root / "prospective_test-metrics.csv")
    inventory = json.loads((root / "prospective-inventory.json").read_text())
    validity = {
        r["seed"]: all(x["numerical_valid"] for x in inventory if x["seed"] == r["seed"])
        for r in inventory
    }
    valid = [s for s, v in sorted(validity.items()) if v]
    selected = json.loads((root / "selection.json").read_text())
    primary = next(
        r
        for r in json.loads((root / "training.json").read_text())
        if r["id"] == selected["primary"]
    )

    def values(model, grid, stratum):
        result = []
        for seed in valid:
            found = [
                float(r["uv_loss"])
                for r in m
                if r["model"] == model
                and int(r["seed"]) == seed
                and r["grid"] == str(grid)
                and r["stratum"] == stratum
                and r["uv_loss"] not in ("", "None")
            ]
            require(len(found) == 2, "QR13 both paired policies per seed")
            result.append(float(np.mean(found)))
        return result

    result = dict(
        valid_families=valid,
        invalid_families=[s for s, v in validity.items() if not v],
        G1=json.loads((root / "dataset-verification.json").read_text())["G1"],
    )
    comparisons = {}
    for gate, reference, stratum in (
        ("G2", selected["baseline"], "all"),
        ("G3", selected["state_only"], "event_crossing"),
    ):
        if len(valid) < 6:
            result[gate] = "INDETERMINATE"
            comparisons[gate] = dict(reason="fewer than6 fully valid prospective seed families")
            continue
        p = paired_test(values(reference, 48, stratum), values(primary["id"], 48, stratum))
        f = paired_test(values(reference, 96, stratum), values(primary["id"], 96, stratum))
        replication = []
        for seed in (23, 29):
            model = f"global_1_{primary['kind']}_{seed}"
            ref = reference if gate == "G2" else f"global_0_{primary['kind']}_{seed}"
            replication.append(
                dict(
                    training_seed=seed,
                    primary=paired_test(values(ref, 48, stratum), values(model, 48, stratum))[
                        "relative_improvement"
                    ],
                    fine=paired_test(values(ref, 96, stratum), values(model, 96, stratum))[
                        "relative_improvement"
                    ],
                )
            )
        passed = (
            p["relative_improvement"] >= 0.1
            and p["p_one_sided"] <= 0.05
            and p["bootstrap95"][0] > 0
            and f["relative_improvement"] > 0
            and all(min(r["primary"], r["fine"]) > 0 for r in replication)
        )
        result[gate] = "PASS" if passed else "FAIL"
        comparisons[gate] = dict(primary=p, fine=f, replication=replication)
    result["comparisons"] = comparisons
    result["G5"] = "NOT RUN"
    result["G6"] = "NOT RUN"
    result["discovery_limit"] = (
        "No qualifying frozen learner-generated physical hypothesis "
        "or independent decision experiment."
    )
    save(root / "forecast-verdicts.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("retrospective_test", "prospective_test", "gates"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(gates(a.root) if a.stage == "gates" else len(evaluate(a.root, a.stage)))


if __name__ == "__main__":
    main()
