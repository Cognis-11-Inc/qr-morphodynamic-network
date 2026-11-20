"""Frozen rank-eight PCA/autoencoder dynamics and held-family physical observables."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from analysis.dataset_0013 import arrays, save, sha
from analysis.evaluate_0013 import paired_test
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write
from analysis.models_0013 import Autoencoder, setup
from analysis.structure_0013 import state_rows, stiffness


def components(root, kind):
    with np.load(Path(root) / "models/pca_state.npz") as p:
        mean, scale, basis = p["mean"].copy(), p["scale"].copy(), p["components"][:8].copy()
    if kind == "pca":

        def encode(x):
            return ((x - mean) / scale) @ basis.T

        def decode(z):
            return (z @ basis) * scale + mean
    else:
        model = Autoencoder()
        model.load_state_dict(
            torch.load(
                Path(root) / f"models/autoencoder_{kind}.pt", map_location="cpu", weights_only=True
            )
        )
        model.eval()

        def encode(x):
            with torch.no_grad():
                return (
                    model.encoder(torch.from_numpy(((x - mean) / scale).astype(np.float32)))
                    .numpy()
                    .astype(float)
                )

        def decode(z):
            with torch.no_grad():
                return model.decoder(torch.from_numpy(z.astype(np.float32))).numpy() * scale + mean

    return encode, decode, scale


def state(y):
    shape = y.shape[:-1]
    return y.reshape(*shape, 4, 130)[..., :128].reshape(*shape, 512)


def pairs(root, inventory, part, encode):
    x, y = [], []
    for r in inventory:
        if r["partition"] == part and r["model_eligible"] and r["development_grid"]:
            a = arrays(root, r, "global", False)
            x.append(np.c_[encode(state(a["current"])), np.ones(len(a["current"]))])
            y.append(encode(state(a["y"]).reshape(-1, 512)).reshape(len(a["y"]), 24))
    return np.concatenate(x), np.concatenate(y)


def fit(root):
    root = Path(root)
    setup()
    require(not (root / "latent-selection.json").exists(), "QR13 immutable latent maps")
    inventory = json.loads((root / "inventory.json").read_text())
    records = []
    for kind in ("pca", "17", "23", "29"):
        encode, decode, scale = components(root, kind)
        x, y = pairs(root, inventory, "train", encode)
        vx, vy = pairs(root, inventory, "validation", encode)
        best = None
        target = decode(vy.reshape(-1, 8))
        for penalty in (1e-6, 1e-3, 1.0, 100.0):
            reg = np.eye(9) * penalty
            reg[-1, -1] = 0
            coef = np.linalg.solve(x.T @ x + reg, x.T @ y)
            error = float(np.mean(((decode((vx @ coef).reshape(-1, 8)) - target) / scale) ** 2))
            if best is None or error < best[0]:
                best = error, penalty, coef
        error, penalty, coef = best
        path = root / f"models/latent_map_{kind}.npz"
        np.savez(path, coef=coef)
        records.append(
            dict(
                kind=kind,
                penalty=penalty,
                validation_latent_evolution_loss=error,
                file=str(path.relative_to(root)),
                sha256=sha(path),
            )
        )
    # Align independently trained latent coordinates using development data ONLY.
    training = state_rows(root, inventory, "train")
    reference = components(root, "17")[0](training)
    for kind in ("23", "29"):
        z = components(root, kind)[0](training)
        align = np.linalg.lstsq(np.c_[z, np.ones(len(z))], reference, rcond=None)[0]
        np.savez(root / f"models/latent_alignment_{kind}.npz", coef=align)
    save(root / "latent-selection.json", records)
    return records


def evaluate(root, partition):
    root = Path(root)
    setup()
    inventory = json.loads((root / "inventory.json").read_text())
    if (root / "prospective-inventory.json").exists():
        inventory += json.loads((root / "prospective-inventory.json").read_text())
    metrics = []
    for case in inventory:
        if case["partition"] != partition or not (
            case["model_eligible"] or case.get("prediction_eligible", False)
        ):
            continue
        a = arrays(root, case, "global", False)
        current = state(a["current"])
        target = state(a["y"])
        with np.load(root / "data" / (case["id"] + ".npz")) as data:
            origin = np.arange(2, len(data["time"]) - 10)
            later = np.concatenate((data["u"][origin + 2], data["v"][origin + 2]), axis=-1).reshape(
                len(origin), 512
            )
            palettes = data["palette"][origin]
        for kind in ("pca", "17", "23", "29"):
            encode, decode, scale = components(root, kind)
            z = encode(current)
            recon = decode(z)
            with np.load(root / f"models/latent_map_{kind}.npz") as m:
                coef = m["coef"].copy()
            forecast = decode((np.c_[z, np.ones(len(z))] @ coef).reshape(-1, 8)).reshape(
                len(z), 3, 512
            )
            f = ((forecast - target) / scale) ** 2
            r = ((recon - current) / scale) ** 2
            # Approximate reduced closure; same map twice, no functor claim.
            nextz = (np.c_[z, np.ones(len(z))] @ coef).reshape(len(z), 3, 8)[:, 0]
            twice = (np.c_[nextz, np.ones(len(z))] @ coef).reshape(len(z), 3, 8)[:, 0]
            observed = encode(later)
            closure = float(
                np.linalg.norm(twice - observed) / max(float(np.linalg.norm(observed)), 1e-30)
            )
            true_energy = []
            recon_energy = []
            for t in range(len(z)):
                et = er = 0.0
                for node in range(4):
                    k, _ = stiffness(palettes[t, node])
                    raw = current[t].reshape(4, 128)[node]
                    reduced = recon[t].reshape(4, 128)[node]
                    et += 0.5 * (raw[64:] @ raw[64:] + raw[:64] @ k @ raw[:64])
                    er += 0.5 * (reduced[64:] @ reduced[64:] + reduced[:64] @ k @ reduced[:64])
                true_energy.append(et)
                recon_energy.append(er)
            energy_error = float(
                np.linalg.norm(np.array(recon_energy) - true_energy)
                / max(float(np.linalg.norm(true_energy)), 1e-30)
            )
            alignment = None
            if kind in ("23", "29"):
                with np.load(root / f"models/latent_alignment_{kind}.npz") as align:
                    aligned = np.c_[z, np.ones(len(z))] @ align["coef"]
                reference = components(root, "17")[0](current)
                alignment = float(
                    np.linalg.norm(aligned - reference)
                    / max(float(np.linalg.norm(reference)), 1e-30)
                )
            metrics.append(
                dict(
                    case=case["id"],
                    seed=case["seed"],
                    grid=case["metadata"]["n"],
                    policy=case["metadata"]["policy"],
                    kind=kind,
                    reconstruction=float(r.mean()),
                    forecast=float(f.mean()),
                    ordinary_forecast=float(f[~a["crossing"]].mean()),
                    event_forecast=float(f[a["crossing"]].mean()) if a["crossing"].any() else None,
                    neural_energy_relative_l2=energy_error,
                    two_step_latent_closure_relative_l2=closure,
                    aligned_latent_relative_l2=alignment,
                )
            )
        print("QR13 latent evaluated", case["id"], flush=True)
    csv_write(root / (partition + "-latent.csv"), metrics)
    return metrics


def gates(root):
    from analysis.experiment_0009 import rows

    root = Path(root)
    data = rows(root / "prospective_test-latent.csv")
    forecast = json.loads((root / "forecast-verdicts.json").read_text())
    seeds = forecast["valid_families"]
    result = dict(G4="INDETERMINATE", comparisons={})
    if len(seeds) >= 6:

        def values(kind, grid, field):
            return [
                float(
                    np.mean(
                        [
                            float(r[field])
                            for r in data
                            if r["kind"] == kind and int(r["seed"]) == s and r["grid"] == str(grid)
                        ]
                    )
                )
                for s in seeds
            ]

        passed = True
        for field in ("reconstruction", "forecast"):
            primary = paired_test(values("pca", 48, field), values("17", 48, field))
            fine = paired_test(values("pca", 96, field), values("17", 96, field))
            replicates = [
                paired_test(values("pca", g, field), values(k, g, field))["relative_improvement"]
                for k in ("23", "29")
                for g in (48, 96)
            ]
            passed &= (
                primary["relative_improvement"] >= 0.1
                and primary["p_one_sided"] <= 0.05
                and primary["bootstrap95"][0] > 0
                and fine["relative_improvement"] > 0
                and min(replicates) > 0
            )
            result["comparisons"][field] = dict(
                primary=primary, fine=fine, replicate_improvements=replicates
            )
        result["G4"] = "PASS" if passed else "FAIL"
    save(root / "latent-verdicts.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("fit", "retrospective_test", "prospective_test", "gates"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    if a.stage == "fit":
        fit(a.root)
    elif a.stage == "gates":
        print(gates(a.root))
    else:
        evaluate(a.root, a.stage)


if __name__ == "__main__":
    main()
