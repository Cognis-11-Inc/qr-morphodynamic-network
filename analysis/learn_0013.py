"""Development-only QR13 baselines and bounded PyTorch fitting with sealed selection."""

import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import torch

from analysis.dataset_0013 import arrays, save, sha
from analysis.experiment_0005 import require
from analysis.models_0013 import Predictor, fit_forecast, predict, uv_loss


def combine(root, inventory, part, observer, morphology):
    cases = [
        r
        for r in inventory
        if r["partition"] == part and r["model_eligible"] and r["development_grid"]
    ]
    require(cases, "QR13 development partition available")
    sets = [arrays(root, r, observer, morphology) for r in cases]
    return {key: np.concatenate([s[key] for s in sets]) for key in sets[0]}


def prepare(train, valid):
    # Pool only TRAIN time/history entries when fitting feature normalization.
    mean = train["x"].mean(axis=(0, 1), keepdims=True)
    std = np.maximum(train["x"].std(axis=(0, 1), keepdims=True), 1e-6)
    scale = np.maximum(np.sqrt(np.mean(train["y"] ** 2, axis=(0, 1))), 1e-8)

    def norm(data):
        return (
            ((data["x"] - mean) / std).astype(np.float32),
            data["palette"].astype(np.float32),
            ((data["y"] - data["current"][:, None, :]) / scale)
            .reshape(len(data["y"]), -1)
            .astype(np.float32),
        )

    return norm(train), norm(valid), dict(mean=mean, std=std, scale=scale)


def linear_features(x, p):
    return np.concatenate((x.reshape(len(x), -1), p), axis=1).astype(float)


def baseline_fit(root):
    root = Path(root)
    require(not (root / "baselines.json").exists(), "QR13 freeze baseline fits once")
    inv = json.loads((root / "inventory.json").read_text())
    dest = root / "models"
    dest.mkdir(exist_ok=True)
    records = []
    begun = time.perf_counter()
    for observer in ("local", "global"):
        for morphology in (False, True):
            train = combine(root, inv, "train", observer, morphology)
            valid = combine(root, inv, "validation", observer, morphology)
            tr, va, norm = prepare(train, valid)
            prefix = f"{observer}_{int(morphology)}"
            np.savez(dest / (prefix + "_normalization.npz"), **norm)
            x = linear_features(*tr[:2])
            vx = linear_features(*va[:2])
            center = x.mean(0)
            x -= center
            vx -= center
            u, s, vh = np.linalg.svd(x, full_matrices=False)
            projected = u.T @ tr[2].astype(float)
            # Same delay representation: unrestricted ridge AR and rank-truncated DMD/PCA+linear.
            for family, ranks in (("ridge", (len(s),)), ("pca_dmd", (4, 8, 16, 32))):
                best = None
                for rank in ranks:
                    k = min(rank, len(s))
                    for penalty in (1e-6, 1e-3, 1.0, 100.0):
                        coef = (vh[:k].T * (s[:k] / (s[:k] ** 2 + penalty))) @ projected[:k]
                        intercept = tr[2].mean(0)
                        out = (vx @ coef + intercept).reshape(valid["y"].shape) * norm[
                            "scale"
                        ] + valid["current"][:, None, :]
                        loss = uv_loss(out, valid["y"], norm["scale"])
                        candidate = (loss, k, penalty, coef, intercept)
                        if best is None or loss < best[0]:
                            best = candidate
                loss, k, penalty, coef, intercept = best
                name = f"{prefix}_{family}"
                np.savez_compressed(
                    dest / (name + ".npz"), coef=coef, intercept=intercept, center=center
                )
                records.append(
                    dict(
                        id=name,
                        observer=observer,
                        morphology=morphology,
                        kind=family,
                        rank=k,
                        penalty=penalty,
                        validation_loss=loss,
                        file=str(Path("models") / (name + ".npz")),
                        normalization=str(Path("models") / (prefix + "_normalization.npz")),
                    )
                )
            records.append(
                dict(
                    id=prefix + "_persistence",
                    observer=observer,
                    morphology=morphology,
                    kind="persistence",
                    validation_loss=uv_loss(
                        np.broadcast_to(valid["current"][:, None, :], valid["y"].shape),
                        valid["y"],
                        norm["scale"],
                    ),
                    normalization=str(Path("models") / (prefix + "_normalization.npz")),
                )
            )
            print("QR13 ordinary baselines complete", prefix, flush=True)
    save(root / "baselines.json", records)
    save(
        root / "baseline-cost.json",
        dict(
            seconds=time.perf_counter() - begun,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            dmd_equivalence="PCA of three-lag delay embedding plus ridge evolution: "
            "truncated delay DMD; not an independent discovery.",
        ),
    )
    return records


def train(root):
    root = Path(root)
    require((root / "baselines.json").exists(), "QR13 ordinary baselines precede neural training")
    require(not (root / "selection.json").exists(), "QR13 no refit after selection")
    inv = json.loads((root / "inventory.json").read_text())
    records = []
    begun = time.perf_counter()
    for observer in ("local", "global"):
        for morphology in (False, True):
            trdata = combine(root, inv, "train", observer, morphology)
            vadata = combine(root, inv, "validation", observer, morphology)
            tr, va, _ = prepare(trdata, vadata)
            for kind in ("mlp", "gru"):
                for seed in (17, 23, 29):
                    require(time.perf_counter() - begun < 1800, "QR13 training ceiling")
                    model, record = fit_forecast(tr, va, kind, seed)
                    name = f"{observer}_{int(morphology)}_{kind}_{seed}"
                    path = root / "models" / (name + ".pt")
                    torch.save(model.state_dict(), path)
                    record.update(
                        id=name,
                        observer=observer,
                        morphology=morphology,
                        file=str(path.relative_to(root)),
                        checkpoint_sha256=sha(path),
                        normalization=f"models/{observer}_{int(morphology)}_normalization.npz",
                        features=tr[0].shape[-1],
                        palettes=tr[1].shape[-1],
                        outputs=tr[2].shape[-1],
                        dataset_sha256=sha(root / "inventory.json"),
                    )
                    records.append(record)
                    save(root / "training.json", records)
                    print("QR13 model", name, record["best_validation_loss"], flush=True)
    primary = min(
        [r for r in records if r["observer"] == "global" and r["morphology"] and r["seed"] == 17],
        key=lambda r: r["best_validation_loss"],
    )
    baselines = json.loads((root / "baselines.json").read_text())
    baseline = min(
        [r for r in baselines if r["observer"] == "global" and r["morphology"]],
        key=lambda r: r["validation_loss"],
    )
    state = next(
        r
        for r in records
        if r["observer"] == "global"
        and not r["morphology"]
        and r["seed"] == 17
        and r["kind"] == primary["kind"]
    )
    save(
        root / "selection.json",
        dict(
            primary=primary["id"],
            baseline=baseline["id"],
            state_only=state["id"],
            selection="seed17 validation409 u/v only; no final observations",
            seconds=time.perf_counter() - begun,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        ),
    )
    # Registered same-seed replay compares tensors and predictions.
    trdata = combine(root, inv, "train", "global", True)
    vadata = combine(root, inv, "validation", "global", True)
    tr, va, _ = prepare(trdata, vadata)
    repeated, rec = fit_forecast(tr, va, primary["kind"], 17)
    old = load_neural(root, primary)
    delta = float(np.max(abs(predict(old, *va[:2]) - predict(repeated, *va[:2]))))
    torch.save(repeated.state_dict(), root / "models/repeat17.pt")
    save(
        root / "training-repeat.json",
        dict(
            max_prediction_absolute_difference=delta,
            parameter_tensors_equal=all(
                torch.equal(v, repeated.state_dict()[k]) for k, v in old.state_dict().items()
            ),
            seconds=rec["seconds"],
            checkpoint_sha256=sha(root / "models/repeat17.pt"),
            scope="same CPU/software; no cross-platform determinism claim",
        ),
    )
    return records


def load_neural(root, record):
    model = Predictor(record["features"], record["palettes"], record["outputs"], record["kind"])
    model.load_state_dict(
        torch.load(Path(root) / record["file"], map_location="cpu", weights_only=True)
    )
    return model


def forecast(root, record, data):
    root = Path(root)
    with np.load(root / record["normalization"]) as n:
        x = ((data["x"] - n["mean"]) / n["std"]).astype(np.float32)
        if record["kind"] == "persistence":
            pred = np.broadcast_to(data["current"][:, None, :], data["y"].shape).copy()
        elif record["kind"] in ("ridge", "pca_dmd"):
            with np.load(root / record["file"]) as p:
                residual = (linear_features(x, data["palette"]) - p["center"]) @ p["coef"] + p[
                    "intercept"
                ]
            pred = residual.reshape(data["y"].shape) * n["scale"] + data["current"][:, None, :]
        else:
            residual = predict(load_neural(root, record), x, data["palette"])
            pred = residual.reshape(data["y"].shape) * n["scale"] + data["current"][:, None, :]
        return pred, n["scale"].copy()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("baselines", "train"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    {"baselines": baseline_fit, "train": train}[a.stage](a.root)


if __name__ == "__main__":
    main()
