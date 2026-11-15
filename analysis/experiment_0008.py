"""QR8 independent signed/energy decoding, fixed features and external references."""

import argparse
import hashlib
import json
import struct
import time
from pathlib import Path

import numpy as np

from analysis.experiment_0005 import coefficients, fnv, require, rows

TRAIN = (101, 103, 107, 109)
HELD = (127, 131, 137, 139)
SIGNALS = ("S9p", "S27p", "S9m", "S27m", "ABp", "ABm", "ZERO", "B27p")
PAIRS = {
    "LOC": ("S9p", "S27p"),
    "SIGN9": ("S9p", "S9m"),
    "SIGN27": ("S27p", "S27m"),
    "DUAL": ("ABp", "ABm"),
}
TIMES = (0.8, 3.2, 8.0, 16.0, 32.0)
DISTANCES = (1, 2, 3, 4, 6)
FIELDS = 4096 * 64
CHECKED = set()
SPEC = json.loads(Path("docs/EXPERIMENT_0008_REGIONS.json").read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def xyz(i):
    return i % 16, i // 16 % 16, i // 256


def hops(a, b):
    return sum(abs(x - y) for x, y in zip(xyz(a), xyz(b), strict=True))


def geometry():
    result = {}
    for family in ("A", "F"):
        for distance in DISTANCES:
            ids = [
                i
                for i in range(4096)
                if i not in (2182, 2186)
                and (hops(i, 2182) if family == "A" else min(hops(i, 2182), hops(i, 2186)))
                == distance
            ]
            selected = [min(ids)]
            while len(selected) < 6:
                selected.append(
                    max(
                        (i for i in ids if i not in selected),
                        key=lambda i: (min(hops(i, j) for j in selected), -i),
                    )
                )
            result[f"{family}{distance}"] = dict(ids=ids, probes=sorted(selected))
    require(result == SPEC["regions"], "registered geometry / deterministic probe budget")
    return result


def decode(path):
    data = path.read_bytes()
    require(len(data) >= 80 and data[:8] == b"QR8FLD01", "QR8 header")
    version, code, port_a, port_b, amp_a, amp_b, length, fields = struct.unpack_from(
        "<4Q2d2Q", data, 8
    )
    require(
        version == 1 and code < 8 and (port_a, port_b) == (2182, 2186) and fields == FIELDS,
        "QR8 metadata",
    )
    require(
        64 < length <= 5_000_000 and len(data) == 72 + length + 16 * FIELDS + 8, "QR8 exact length"
    )
    digest = hashlib.sha256(data).hexdigest()
    body = data[72 : 72 + length]
    require(body[:8] == b"QR6FLD01", "QR8 unchanged signed field body")
    version, tick, dt, seed, config, size, module = struct.unpack_from("<QQdQQQQ", body, 8)
    signal = SIGNALS[code]
    require(
        version == 1
        and config == 0
        and dt in (0.025, 0.0125)
        and tick * dt <= 32 + 1e-9
        and 0 < size <= 200,
        "QR8 body bounds",
    )
    require(module == (9 if signal in ("S9p", "S9m") else 27), "QR8 input module")
    require(length == 64 + size + 17 * FIELDS + 8, "QR8 body length")
    require(
        body[64 : 64 + size].decode() == f"s{seed}_{signal}", "embedded full condition identity"
    )
    if digest not in CHECKED:
        require(
            fnv(data[:-8]) == struct.unpack_from("<Q", data, len(data) - 8)[0], "QR8 outer checksum"
        )
        require(
            fnv(body[:-8]) == struct.unpack_from("<Q", body, len(body) - 8)[0], "QR8 inner checksum"
        )
        CHECKED.add(digest)
    offset = 64 + size
    p = np.frombuffer(body, "u1", FIELDS, offset).reshape(4096, 8, 8)
    u = np.frombuffer(body, "<f8", FIELDS, offset + FIELDS).reshape(4096, 8, 8)
    v = np.frombuffer(body, "<f8", FIELDS, offset + 9 * FIELDS).reshape(4096, 8, 8)
    k = np.frombuffer(data, "<f8", FIELDS, 72 + length).reshape(4096, 8, 8)
    q = np.frombuffer(data, "<f8", FIELDS, 72 + length + 8 * FIELDS).reshape(4096, 8, 8)
    require(
        p.max() <= 4 and all(np.isfinite(a).all() for a in (u, v, k, q)), "QR8 finite field screen"
    )
    require(
        max(float(np.abs(u).max()), float(np.abs(v).max())) <= 100
        and min(float(k.min()), float(q.min())) >= 0,
        "QR8 bounds",
    )
    return dict(
        palette=p,
        u=u,
        v=v,
        k=k,
        q=q,
        seed=seed,
        dt=dt,
        tick=tick,
        module=module,
        signal=signal,
        amplitudes=(amp_a, amp_b),
        sha256=digest,
    )


def partitions(p, u, v):
    """Independent half-edge partition; no Rust edge ordering/list is used."""
    omega2, _, g = coefficients(p)
    k = 0.5 * v * v
    onsite = 0.5 * omega2 * u * u
    q = onsite.copy()
    coupling = 0.0
    for field, conductance, potential, axes, coefficient in (
        (u, g, q, (1, 2), 0.15),
        (
            u.reshape(16, 16, 16, 8, 8),
            g.reshape(16, 16, 16, 8, 8),
            q.reshape(16, 16, 16, 8, 8),
            (0, 1, 2),
            0.4 / 6,
        ),
    ):
        for axis in axes:
            left, right = [slice(None)] * field.ndim, [slice(None)] * field.ndim
            left[axis], right[axis] = slice(None, -1), slice(1, None)
            left, right = tuple(left), tuple(right)
            energy = (
                0.5
                * coefficient
                * conductance[left]
                * conductance[right]
                * (field[left] - field[right]) ** 2
            )
            coupling += float(energy.sum())
            potential[left] += 0.5 * energy
            potential[right] += 0.5 * energy
    return k, q, k + onsite, (float(k.sum()), float(onsite.sum()), coupling)


def checkpoint(root, stage, seed, signal, t):
    folder = root / stage / f"s{seed}_{signal}"
    dt = float(rows(folder / "parameters.csv")[0]["dt"])
    return decode(folder / f"{round(t / dt):06}.q8f")


def relative(a, b):
    return float(np.linalg.norm(a - b) / max(float(np.linalg.norm(b)), 1e-30))


def layouts():
    yield "G", None, "all", "G"
    for region in SPEC["regions"]:
        for mask in ("all", "cross"):
            for rep in ("T", "U", "KP", "UV", "SH"):
                yield f"{region}_{mask}_{rep}", region, mask, rep


def extract_features(frames):
    result = {key: [] for key, _, _, _ in layouts()}
    for frame in frames:
        e = frame["k"] + frame["q"]
        result["G"].append(float(e.sum()))
        for key, region, mask, rep in layouts():
            if region is None:
                continue
            ids = SPEC["regions"][region]["probes"]
            modules = [m for m in range(64) if mask == "all" or m not in (9, 27)]
            if rep == "SH":
                all_ids = SPEC["regions"][region]["ids"]
                result[key].append(float(e.reshape(4096, 64)[np.ix_(all_ids, modules)].sum()))
                continue
            a = {"T": e, "U": frame["u"], "KP": frame["k"], "UV": frame["u"]}[rep].reshape(
                4096, 64
            )[np.ix_(ids, modules)]
            if rep in ("KP", "UV"):
                b = (frame["q"] if rep == "KP" else frame["v"]).reshape(4096, 64)[
                    np.ix_(ids, modules)
                ]
                a = np.stack((a, b), axis=-1)
            result[key].extend(a.ravel().tolist())
    return {key: np.array(values, dtype="<f8") for key, values in result.items()}


def feature(root, stage, seed, signal, key):
    return np.fromfile(root / "features" / stage / f"s{seed}_{signal}" / (key + ".f64"), "<f8")


def fit(vectors):
    require(set(vectors) == set(TRAIN), "reference fitting accepts training seeds only")
    shape = np.asarray(vectors[TRAIN[0]]).shape
    require(len(shape) == 2 and shape[0] == 2, "reference shape")
    means = np.zeros(shape)
    for seed in TRAIN:
        x = np.asarray(vectors[seed])
        require(x.shape == shape and np.isfinite(x).all(), "finite reference vectors")
        means += x
    return means / 4


def predict(x, means):
    """Numeric arrays only: no condition, seed, palette or expected label input."""
    x, means = np.asarray(x), np.asarray(means)
    require(
        x.ndim == 1
        and means.shape == (2, len(x))
        and np.isfinite(x).all()
        and np.isfinite(means).all(),
        "decoder input",
    )
    d = np.sum((means - x) ** 2, axis=1)
    require(np.isfinite(d).all(), "finite distances")
    result = (
        None if abs(float(d[0] - d[1])) <= 1e-12 * max(float(d.max()), 1e-30) else int(d[1] < d[0])
    )
    return result, [float(value) for value in d]


def freeze(root):
    require(not (root / "train/TRAINING_FROZEN").exists(), "reference templates already frozen")
    while not (root / "audit/TRAIN_READY").exists():
        time.sleep(2)
    models = root / "models"
    models.mkdir()
    metadata = []
    for pair, signals in PAIRS.items():
        for key, region, mask, rep in layouts():
            vectors = {
                seed: np.array([feature(root, "train", seed, s, key) for s in signals])
                for seed in TRAIN
            }
            means = fit(vectors)
            filename = f"{pair}_{key}.f64"
            means.astype("<f8").tofile(models / filename)
            metadata.append(
                dict(
                    pair=pair,
                    key=key,
                    region=region,
                    mask=mask,
                    rep=rep,
                    dimension=means.shape[1],
                    file=filename,
                    sha256=sha(models / filename),
                )
            )
    require(len(metadata) == 404, "complete fixed reference matrix")
    receipt = dict(
        schema=1, training_seeds=TRAIN, models=metadata, method_source_sha256=sha(Path(__file__))
    )
    (models / "freeze.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (root / "train/TRAINING_FROZEN").write_text(
        "QR8_TRAINING_FROZEN_SCHEMA1\n" + sha(models / "freeze.json") + "\n"
    )
    print("FROZEN 404 external reference pairs; held-out observations never fitted", flush=True)


def evaluate(root, physical):
    receipt = json.loads((root / "models/freeze.json").read_text())
    require(tuple(receipt["training_seeds"]) == TRAIN, "frozen split")
    require(
        receipt["method_source_sha256"] == sha(Path(__file__)), "frozen measurement method changed"
    )
    require(
        (root / "train/TRAINING_FROZEN").read_text()
        == "QR8_TRAINING_FROZEN_SCHEMA1\n" + sha(root / "models/freeze.json") + "\n",
        "frozen receipt",
    )
    results = []
    predictions = []
    for model in receipt["models"]:
        file = root / "models" / model["file"]
        require(sha(file) == model["sha256"], "reference means changed")
        means = np.fromfile(file, "<f8").reshape(2, model["dimension"])
        signals = PAIRS[model["pair"]]
        expected = fit(
            {
                seed: np.array([feature(root, "train", seed, s, model["key"]) for s in signals])
                for seed in TRAIN
            }
        )
        require(np.array_equal(means, expected), "independent train-only reference means")
        counts = {}
        outputs = {}
        for stage, seeds in (("train", TRAIN), ("evaluate", HELD), ("refine", HELD)):
            correct = ties = 0
            for seed in seeds:
                for label, signal in enumerate(signals):
                    answer, d = predict(feature(root, stage, seed, signal, model["key"]), means)
                    correct += answer == label
                    ties += answer is None
                    outputs[(stage, seed, label)] = answer
                    predictions.append(
                        dict(
                            pair=model["pair"],
                            key=model["key"],
                            stage=stage,
                            seed=seed,
                            signal=signal,
                            expected=label,
                            prediction=answer,
                            d0=d[0],
                            d1=d[1],
                        )
                    )
            counts[stage] = dict(correct=correct, total=8, ties=ties)
        margins = []
        field_ok = True
        for seed in HELD:
            x = [
                [feature(root, stage, seed, s, model["key"]) for s in signals]
                for stage in ("evaluate", "refine")
            ]
            separation = float(np.linalg.norm(x[1][1] - x[1][0]))
            error = max(float(np.linalg.norm(x[0][i] - x[1][i])) for i in (0, 1))
            rel = max(relative(x[0][i], x[1][i]) for i in (0, 1))
            floor = 1e-6 if model["rep"] in ("U", "UV") else 1e-8
            margins.append(
                dict(
                    seed=seed,
                    separation=separation,
                    disagreement=error,
                    relative_error=rel,
                    detected=separation > floor,
                    resolved=separation >= 5 * error,
                )
            )
            field_ok &= all(physical[f"{seed}/{s}"]["pass_gate"] for s in signals)
        consistency = all(
            outputs[("evaluate", seed, i)] == outputs[("refine", seed, i)]
            for seed in HELD
            for i in (0, 1)
        )
        if not field_ok or any(m["relative_error"] > 0.05 for m in margins):
            verdict = "INDETERMINATE"
        elif any(not m["detected"] for m in margins):
            verdict = "FAIL"
        elif any(not m["resolved"] for m in margins):
            verdict = "INDETERMINATE"
        elif not consistency or any(
            counts[stage]["correct"] < 7 or counts[stage]["ties"]
            for stage in ("evaluate", "refine")
        ):
            verdict = "FAIL"
        else:
            verdict = "PASS"
        results.append(
            dict(
                **model,
                counts=counts,
                margins=margins,
                field_valid=field_ok,
                predictions_consistent=consistency,
                verdict=verdict,
            )
        )
    return results, predictions


def review(root):
    """Portable numerical classifier review; full-field gates are stored evidence."""
    stored = json.loads((root / "verification.json").read_text())
    results, predictions = evaluate(root, stored["refinement"])
    require(
        results == stored["decoders"] and predictions == stored["predictions"],
        "portable numerical readout reproduction",
    )
    return dict(
        models=len(results),
        predictions=len(predictions),
        scope="numeric readouts remeasured; full-field gates require signed archive",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("action", choices=("fit", "review"))
    args = parser.parse_args()
    if args.action == "fit":
        freeze(args.root)
    else:
        print(json.dumps(review(args.root), indent=2))


if __name__ == "__main__":
    main()
