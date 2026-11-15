"""Independent numeric-only QR7 readout and held-out verdicts.

This module never fits on evaluation or refinement observations. Checkpoint
metadata is validated separately and cannot enter the numeric decoder.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

from analysis.experiment_0005 import fnv, require, rows

TRAIN = (7, 19, 31, 43)
HELD = (59, 71, 83, 97)
TIMES = (0.8, 3.2, 8, 16, 32)
OUTPUTS = (2184, 2185, 2186)
CONTROLS = (
    "VIRGIN",
    "ALL",
    "WRITE_PORT_ONLY",
    "READ_PORT_ONLY",
    "REMOTE_ONLY",
    "SHUFFLED",
    "FROZEN",
    "NO_WRITE",
)
FIELDS = 4096 * 64


def predict(x, means):
    """Pure 120-float input, two frozen means, no metadata or expected answer."""
    x, means = np.asarray(x), np.asarray(means)
    require(x.shape == (120,) and means.shape == (2, 120), "decoder dimensions")
    require(np.isfinite(x).all() and np.isfinite(means).all(), "decoder finite")
    # Match the registered component order; no normalization or learned metric.
    distances = [sum(float(a - b) ** 2 for a, b in zip(x, mean, strict=True)) for mean in means]
    require(np.isfinite(distances).all(), "distance overflow")
    d0, d1 = distances
    prediction = None if abs(d0 - d1) <= 1e-12 * max(d0, d1, 1e-30) else int(d1 < d0)
    return prediction, distances


def fit(vectors):
    """Only the explicitly keyed four training seeds are accepted."""
    require(set(vectors) == set(TRAIN), "training isolation")
    means = np.zeros((2, 120))
    for seed in TRAIN:
        values = np.asarray(vectors[seed])
        require(values.shape == (2, 120) and np.isfinite(values).all(), "training vectors")
        means += values
    return means / 4


def decode(path):
    data = path.read_bytes()
    require(len(data) >= 112 and data[:8] == b"QR7FLD01", "QR7 magic")
    version, port, operation, rule = struct.unpack_from("<4Q", data, 8)
    require(version == 1 and operation in (0, 1, 2) and rule in (0, 2, 3), "QR7 operation")
    require(port == (2182 if operation == 1 else 2183), "QR7 physical port")
    require(fnv(data[:-8]) == struct.unpack_from("<Q", data, len(data) - 8)[0], "QR7 checksum")
    b = data[40:-8]
    require(b[:8] == b"QR6FLD01", "QR7 signed body")
    version, tick, dt, seed, config, length, module = struct.unpack_from("<QQdQQQQ", b, 8)
    require(version == 1 and config == 2 and 0 < length <= 200, "QR7 body metadata")
    require(dt in (0.025, 0.0125) and module in (9, 27) and tick <= 2560, "QR7 grid")
    require(len(b) == 64 + length + 17 * FIELDS + 8, "QR7 exact body length")
    require(fnv(b[:-8]) == struct.unpack_from("<Q", b, len(b) - 8)[0], "QR7 body checksum")
    offset = 64 + length
    p = np.frombuffer(b, "u1", FIELDS, offset).reshape(4096, 8, 8)
    u = np.frombuffer(b, "<f8", FIELDS, offset + FIELDS).reshape(4096, 8, 8)
    v = np.frombuffer(b, "<f8", FIELDS, offset + 9 * FIELDS).reshape(4096, 8, 8)
    require(np.max(p) <= 4 and np.isfinite(u).all() and np.isfinite(v).all(), "QR7 bounded fields")
    require(max(float(np.abs(u).max()), float(np.abs(v).max())) <= 100, "QR7 finite screen")
    return dict(
        palette=p,
        u=u,
        v=v,
        tick=tick,
        dt=dt,
        seed=seed,
        module=module,
        operation=operation,
        rule=rule,
        port=port,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def resolve(stage, ident):
    folder = stage / ident
    if (folder / "REUSED").exists():
        reference = (folder / "REUSED").read_text()
        require("/" not in reference and ".." not in reference, "reuse reference")
        require((folder / "EQUIVALENT").exists(), "reuse equivalence proof")
        folder = stage / reference
    require((folder / "COMPLETE").exists(), "incomplete trajectory " + ident)
    return folder


def checkpoint(stage, ident, time):
    folder = resolve(stage, ident)
    dt = float(rows(folder / "parameters.csv")[0]["dt"])
    return decode(folder / f"{round(time / dt):06}.q7f")


def feature(stage, ident):
    values = []
    for pulse in (9, 27):
        for time in TIMES:
            frame = checkpoint(stage, f"{ident}_p{pulse}", time)
            for site in OUTPUTS:
                for module in (9, 27):
                    values.extend(
                        (
                            float(frame["u"].reshape(4096, 64)[site, module]),
                            float(frame["v"].reshape(4096, 64)[site, module]),
                        )
                    )
    x = np.array(values)
    stored = np.fromfile(stage / f"{ident}.f64", dtype="<f8")
    require(np.array_equal(x, stored), "120 signed feature reconstruction " + ident)
    return x


def ident(seed, rule, symbol, kind):
    return f"s{seed}_r{rule}_w{symbol}_{kind}"


def vector(stage, seed, rule, symbol, kind):
    return np.fromfile(stage / f"{ident(seed, rule, symbol, kind)}.f64", dtype="<f8")


def relative(a, b):
    return float(np.linalg.norm(a - b) / max(float(np.linalg.norm(b)), 1e-30))


def analyse(root):
    """Independent fit/prediction/refinement; measurements remain separate gates."""
    train, coarse, fine = (root / name for name in ("train", "evaluate", "refine"))
    for stage in (train, coarse, fine):
        require((stage / "COMPLETE").exists(), "complete registered stage")
    result = {"models": [], "margins": [], "remote_influence": [], "predictions": []}
    for rule in (2, 3):
        for calibrated in (True, False):
            training = {}
            for seed in TRAIN:
                baseline = np.fromfile(train / f"s{seed}_CALIBRATE.f64", dtype="<f8")
                training[seed] = np.array(
                    [
                        vector(train, seed, rule, s, "REMOTE_ONLY")
                        - (baseline if calibrated else 0)
                        for s in (0, 1)
                    ]
                )
            means = fit(training)
            suffix = "calibrated" if calibrated else "raw"
            stored = np.fromfile(train / f"template_r{rule}_{suffix}.f64", dtype="<f8").reshape(
                2, 120
            )
            require(np.array_equal(means, stored), "frozen training means independently derived")
            counts = {}
            remote_predictions = {}
            for stage, seeds in ((train, TRAIN), (coarse, HELD), (fine, HELD)):
                emitted = {(r["id"], r["calibrated"]): r for r in rows(stage / "predictions.csv")}
                kinds = ("REMOTE_ONLY",) if stage == fine else CONTROLS
                for kind in kinds:
                    correct, ties = 0, 0
                    for seed in seeds:
                        base = np.fromfile(stage / f"s{seed}_CALIBRATE.f64", dtype="<f8")
                        for symbol in (0, 1):
                            name = ident(seed, rule, symbol, kind)
                            x = vector(stage, seed, rule, symbol, kind) - (
                                base if calibrated else 0
                            )
                            prediction, distances = predict(x, means)
                            recorded = emitted[(name, str(calibrated).lower())]
                            actual = (
                                None
                                if recorded["prediction"] == "AMBIGUOUS"
                                else int(recorded["prediction"])
                            )
                            require(
                                actual == prediction and int(recorded["expected"]) == symbol,
                                "independent prediction",
                            )
                            require(
                                np.allclose(
                                    distances,
                                    [float(recorded["d0"]), float(recorded["d1"])],
                                    rtol=1e-13,
                                    atol=1e-30,
                                ),
                                "distance audit",
                            )
                            correct += prediction == symbol
                            ties += prediction is None
                            if kind == "REMOTE_ONLY":
                                remote_predictions[(stage.name, seed, symbol)] = prediction
                            result["predictions"].append(
                                dict(
                                    stage=stage.name,
                                    rule=rule,
                                    calibrated=calibrated,
                                    kind=kind,
                                    seed=seed,
                                    expected=symbol,
                                    prediction=prediction,
                                    distances=distances,
                                )
                            )
                    counts[f"{stage.name}/{kind}"] = dict(correct=correct, total=8, ties=ties)
            margin_pass = True
            for seed in HELD:
                xs = []
                for stage in (coarse, fine):
                    base = np.fromfile(stage / f"s{seed}_CALIBRATE.f64", dtype="<f8")
                    xs.append(
                        [
                            vector(stage, seed, rule, s, "REMOTE_ONLY")
                            - (base if calibrated else 0)
                            for s in (0, 1)
                        ]
                    )
                separation = float(np.linalg.norm(xs[1][1] - xs[1][0]))
                errors = [float(np.linalg.norm(xs[0][s] - xs[1][s])) for s in (0, 1)]
                rel = [relative(xs[0][s], xs[1][s]) for s in (0, 1)]
                passed = separation > 1e-10 and separation >= 5 * max(errors) and max(rel) <= 0.05
                margin_pass &= passed
                result["margins"].append(
                    dict(
                        seed=seed,
                        rule=rule,
                        calibrated=calibrated,
                        separation=separation,
                        refinement_error=max(errors),
                        relative_errors=rel,
                        pass_gate=passed,
                    )
                )
            consistency = all(
                remote_predictions[("evaluate", seed, s)] == remote_predictions[("refine", seed, s)]
                for seed in HELD
                for s in (0, 1)
            )
            accuracy = all(
                counts[f"{stage}/REMOTE_ONLY"]["correct"] >= 7
                and counts[f"{stage}/REMOTE_ONLY"]["ties"] == 0
                for stage in ("evaluate", "refine")
            )
            result["models"].append(
                dict(
                    rule=rule,
                    calibrated=calibrated,
                    counts=counts,
                    predictions_consistent=consistency,
                    margin_pass=margin_pass,
                    decoder_pass=accuracy and consistency and margin_pass,
                )
            )
        for seed in HELD:
            for symbol in (0, 1):
                contrasts = []
                field_errors = []
                for stage in (coarse, fine):
                    base = np.fromfile(stage / f"s{seed}_CALIBRATE.f64", dtype="<f8")
                    contrasts.append(
                        relative(vector(stage, seed, rule, symbol, "REMOTE_ONLY"), base)
                    )
                for pulse in (9, 27):
                    name = ident(seed, rule, symbol, "REMOTE_ONLY") + f"_p{pulse}"
                    for time in TIMES:
                        a, b = checkpoint(coarse, name, time), checkpoint(fine, name, time)
                        field_errors.append(
                            relative(
                                np.concatenate((a["u"].ravel(), a["v"].ravel())),
                                np.concatenate((b["u"].ravel(), b["v"].ravel())),
                            )
                        )
                a = decode(coarse / ident(seed, rule, symbol, "WRITE") / "post.q7f")["palette"]
                b = decode(fine / ident(seed, rule, symbol, "WRITE") / "post.q7f")["palette"]
                virgin = checkpoint(coarse, f"s{seed}_CALIBRATE_p9", 0)["palette"]
                ca, cb = a != virgin, b != virgin
                union = int(np.count_nonzero(ca | cb))
                jaccard = float(np.count_nonzero(ca & cb) / union) if union else 1.0
                result["remote_influence"].append(
                    dict(
                        seed=seed,
                        rule=rule,
                        symbol=symbol,
                        raw_relative_contrasts=contrasts,
                        maximum_field_error=max(field_errors),
                        edit_jaccard=jaccard,
                        palette_equal=bool(np.array_equal(a, b)),
                        influence_pass=min(contrasts) >= 0.01,
                        numerical_pass=max(field_errors) <= 0.015 and jaccard >= 0.9,
                    )
                )
    numerical = all(r["numerical_pass"] for r in result["remote_influence"])
    result["refinement_pass"] = numerical
    for model in result["models"]:
        model["operational_pass"] = model["decoder_pass"] and numerical
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = analyse(args.root)
    path = args.root / "readout-verification.json"
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("predictions",)}, indent=2))


if __name__ == "__main__":
    main()
