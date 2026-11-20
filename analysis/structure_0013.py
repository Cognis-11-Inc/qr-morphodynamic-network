"""Ordinary QR13 physical reduction, spectral/PCA and latent-structure measurements."""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from analysis.dataset_0013 import HORIZONS, arrays, save, sha
from analysis.experiment_0005 import require


def stiffness(palette):
    p = np.asarray(palette)
    k = np.zeros((64, 64))
    gamma = np.empty(64)
    gain = np.choose(p, [0.5, 1.0, 0.75, 0.75, 0.75])
    for m in range(64):
        neighbors = [j for j in range(64) if abs(j // 8 - m // 8) + abs(j % 8 - m % 8) == 1]
        k[m, m] = (
            0.8 + 0.08 * p[m] + 0.04 * np.count_nonzero(p[neighbors]) + (0.12 if p[m] == 1 else 0)
        ) ** 2
        gamma[m] = 0.08 + 0.01 * np.count_nonzero(p[neighbors] == 0) + (0 if p[m] == 1 else 0.02)
        for j in neighbors:
            weight = 0.15 * gain[m] * gain[j]
            k[m, m] += weight
            k[m, j] -= weight
    return k, gamma


def physical_predict(root, record, observer="global"):
    arrays(root, record, observer, True)
    with np.load(Path(root) / "data" / (record["id"] + ".npz")) as a:
        origins = np.arange(2, len(a["time"]) - 10)
        result = np.zeros((len(origins), 3, 4, 130))
        for row, t in enumerate(origins):
            for node in range(4):
                k, gamma = stiffness(a["palette"][t, node])
                u, v = a["u"][t, node], a["v"][t, node]
                acc = -k @ u - gamma * v
                acc[[9, 27]] -= 0.1 * a["packet"][t, node, 0]
                kind = record["metadata"]["forcing"]
                physical_time = a["time"][t]
                force = np.sin(2 * np.pi * physical_time / 8)
                force *= (
                    np.sin(np.pi * physical_time / 8) ** 2
                    if kind.startswith("SUSTAINED") and physical_time < 4
                    else 1
                    if kind.startswith("SUSTAINED")
                    else np.sin(np.pi * physical_time / 12) ** 2
                    if physical_time <= 12
                    else 0
                )
                if kind == "QUIET":
                    force = 0.0
                if kind == "COMMON":
                    acc[9] += 0.5 * force
                elif node == 0:
                    acc[9] += force
                for h, H in enumerate(HORIZONS):
                    pu = u + H * v + 0.5 * H * H * acc
                    pv = v + H * acc
                    result[row, h, node, :64] = pu
                    result[row, h, node, 64:128] = pv
                    result[row, h, node, 128] = a["packet"][t, node, 0]
                    result[row, h, node, 129] = 0.5 * (pv @ pv + pu @ k @ pu)
    if observer == "global":
        result = result.reshape(len(origins), 3, -1)
    else:
        result = result.transpose(0, 2, 1, 3).reshape(-1, 3, 130)
    return result


def physical_baseline(root):
    from analysis.learn_0013 import combine
    from analysis.models_0013 import uv_loss

    root = Path(root)
    inv = json.loads((root / "inventory.json").read_text())
    records = json.loads((root / "baselines.json").read_text())
    started = time.perf_counter()
    for observer in ("local", "global"):
        validation = combine(root, inv, "validation", observer, True)
        predictions = [
            physical_predict(root, r, observer)
            for r in inv
            if r["partition"] == "validation" and r["model_eligible"] and r["development_grid"]
        ]
        with np.load(root / f"models/{observer}_1_normalization.npz") as n:
            loss = uv_loss(np.concatenate(predictions), validation["y"], n["scale"])
        records.append(
            dict(
                id=f"{observer}_1_physical",
                observer=observer,
                morphology=True,
                kind="physical",
                validation_loss=loss,
                normalization=f"models/{observer}_1_normalization.npz",
            )
        )
    save(root / "baselines.json", records)
    save(root / "physical-baseline-cost.json", dict(seconds=time.perf_counter() - started))


def state_rows(root, inventory, partition, primary_only=True):
    cases = [
        r
        for r in inventory
        if r["partition"] == partition
        and r["model_eligible"]
        and (r["development_grid"] or not primary_only)
    ]
    values = []
    for r in cases:
        with np.load(Path(root) / "data" / (r["id"] + ".npz")) as a:
            values.append(np.concatenate((a["u"], a["v"]), axis=-1).reshape(len(a["time"]), 512))
    require(values, "QR13 latent partition")
    return np.concatenate(values)


def ordinary(root):
    root = Path(root)
    inv = json.loads((root / "inventory.json").read_text())
    train = state_rows(root, inv, "train")
    mean = train.mean(0)
    scale = np.maximum(np.sqrt(np.mean(train**2, 0)), 1e-8)
    _, s, vh = np.linalg.svd((train - mean) / scale, full_matrices=False)
    np.savez(root / "models/pca_state.npz", mean=mean, scale=scale, components=vh[:32])
    cases = []
    for r in inv:
        if not r["model_eligible"]:
            continue
        with np.load(root / "data" / (r["id"] + ".npz")) as a:
            velocity = a["v"][:, :, 9]
            freq = np.fft.rfftfreq(len(velocity), 0.2)
            powers = abs(np.fft.rfft(velocity, axis=0)) ** 2
            rms = np.sqrt(np.mean(velocity**2, axis=0))
            pairs = []
            spectrum = np.fft.fft(velocity, axis=0)
            filt = np.zeros(len(velocity))
            filt[0] = 1
            filt[1 : (len(velocity) + 1) // 2] = 2
            if len(velocity) % 2 == 0:
                filt[len(velocity) // 2] = 1
            phase = np.angle(np.fft.ifft(spectrum * filt[:, None], axis=0))
            for i in range(4):
                for j in range(i + 1, 4):
                    if min(rms[i], rms[j]) >= 1e-8:
                        pairs.append(
                            dict(
                                i=i,
                                j=j,
                                correlation=float(
                                    np.corrcoef(velocity[:, i], velocity[:, j])[0, 1]
                                ),
                                phase_lock=float(
                                    abs(np.mean(np.exp(1j * (phase[:, i] - phase[:, j]))))
                                ),
                            )
                        )
            cases.append(
                dict(
                    id=r["id"],
                    partition=r["partition"],
                    rms=rms.tolist(),
                    dominant_frequency=freq[np.argmax(powers, axis=0)].tolist(),
                    pairs=pairs,
                    undefined_pairs=6 - len(pairs),
                )
            )
    save(
        root / "ordinary-structure.json",
        dict(
            train_singular_values=s.tolist(),
            cumulative_variance=(np.cumsum(s * s) / np.sum(s * s)).tolist(),
            cases=cases,
        ),
    )
    return cases


def latent_fit(root):
    import torch

    from analysis.models_0013 import Autoencoder, setup

    root = Path(root)
    inv = json.loads((root / "inventory.json").read_text())
    require(not (root / "latent-models.json").exists(), "QR13 one latent selection")
    with np.load(root / "models/pca_state.npz") as n:
        mean = n["mean"]
        scale = n["scale"]
    x = ((state_rows(root, inv, "train") - mean) / scale).astype(np.float32)
    v = ((state_rows(root, inv, "validation") - mean) / scale).astype(np.float32)
    records = []
    for seed in (17, 23, 29):
        setup(seed)
        model = Autoencoder()
        opt = torch.optim.Adam(model.parameters(), lr=0.001)
        rng = np.random.default_rng(seed)
        best = float("inf")
        begun = time.perf_counter()
        history = []
        for epoch in range(1, 121):
            model.train()
            for indices in np.array_split(
                rng.permutation(len(x)), max(1, int(np.ceil(len(x) / 256)))
            ):
                inp = torch.from_numpy(x[indices])
                opt.zero_grad(set_to_none=True)
                loss = ((model(inp) - inp) ** 2).mean()
                loss.backward()
                opt.step()
            if epoch % 5 == 0:
                model.eval()
                with torch.no_grad():
                    val = float(((model(torch.from_numpy(v)) - torch.from_numpy(v)) ** 2).mean())
                history.append(dict(epoch=epoch, validation=val))
                if val < best:
                    best = val
                    weights = {k: t.detach().clone() for k, t in model.state_dict().items()}
        model.load_state_dict(weights)
        path = root / f"models/autoencoder_{seed}.pt"
        torch.save(weights, path)
        records.append(
            dict(
                seed=seed,
                file=str(path.relative_to(root)),
                checkpoint_sha256=sha(path),
                validation_reconstruction=best,
                seconds=time.perf_counter() - begun,
                parameters=sum(t.numel() for t in model.parameters()),
                history=history,
            )
        )
    save(root / "latent-models.json", records)
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("ordinary", "latent", "physical"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    {"ordinary": ordinary, "latent": latent_fit, "physical": physical_baseline}[a.stage](a.root)


if __name__ == "__main__":
    main()
