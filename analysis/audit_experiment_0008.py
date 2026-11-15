"""Independent QR8 energy, stream, symmetry, transport and readout verification."""

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

from analysis import experiment_0008 as q
from analysis.experiment_0005 import require, rows

SOURCES = (
    "analysis/audit_experiment_0008.py",
    "analysis/experiment_0008.py",
    "analysis/experiment_0005.py",
    "src/communication_0008.rs",
    "src/morphic_0006.rs",
    "src/bin/experiment_0008.rs",
    "EXPERIMENT_0008.md",
    "docs/EXPERIMENT_0008_REGIONS.json",
)
SOURCE_SHA = hashlib.sha256(b"".join(Path(p).read_bytes() for p in SOURCES)).hexdigest()
REGIONS = q.geometry()


def module_streams(folder):
    with (folder / "regions.q8r").open("rb") as stream:
        require(stream.read(8) == b"QR8REG01", "region magic")
        require(np.array_equal(np.frombuffer(stream.read(24), "<u8"), [1, 10, 12]), "region schema")
    dtype = np.dtype([("tick", "<u8"), ("values", "<f8", (10, 12))])
    require(((folder / "regions.q8r").stat().st_size - 32) % dtype.itemsize == 0, "region length")
    region = np.memmap(folder / "regions.q8r", mode="r", dtype=dtype, offset=32)
    with (folder / "probes.q8p").open("rb") as stream:
        require(stream.read(8) == b"QR8PRB01", "probe magic")
        version, count, modules = np.frombuffer(stream.read(24), "<u8")
        require(version == 1 and count == 50 and modules == 4, "probe dimensions")
        ids = np.frombuffer(stream.read(int(count) * 8), "<u8").astype(int)
        mods = np.frombuffer(stream.read(32), "<u8").astype(int)
    require(
        ids.tolist() == q.SPEC["streamed_probes"] and mods.tolist() == [9, 27, 10, 18],
        "fixed probe identities",
    )
    offset = 32 + 8 * (len(ids) + len(mods))
    dtype = np.dtype([("tick", "<u8"), ("values", "<f8", (len(ids), 10))])
    require(((folder / "probes.q8p").stat().st_size - offset) % dtype.itemsize == 0, "probe length")
    probes = np.memmap(folder / "probes.q8p", mode="r", dtype=dtype, offset=offset)
    return region, probes, ids, mods


def region_values(e, motion, other, other_m, cross, cross_m, total, name):
    ids = REGIONS[name]["ids"]
    neuron = e.sum(axis=(1, 2))
    arrays = [a.sum(axis=(1, 2)) for a in (motion, other, other_m, cross, cross_m)]
    receiver = float(neuron[ids].sum())
    return np.array(
        [
            receiver + (float(neuron[2186]) if name == "A4" else 0),
            receiver,
            receiver / total if total else 0,
            float(arrays[0][ids].sum()),
            float(arrays[1][ids].sum()),
            float(arrays[2][ids].sum()),
            float(arrays[3][ids].sum()),
            float(arrays[4][ids].sum()),
            float(neuron[ids].min()),
            float(neuron[ids].max()),
            float(neuron[ids].mean()),
            float(neuron[ids].std()),
        ]
    )


def audit_case(root, stage, folder):
    params = rows(folder / "parameters.csv")[0]
    seed, dt, signal = int(params["seed"]), float(params["dt"]), params["signal"]
    require(folder.name == f"s{seed}_{signal}" and params["id"] == folder.name, "case identity")
    metrics = rows(folder / "metrics.csv")
    require(len(metrics) == round(32 / dt) + 1, "every-tick horizon")
    region, probes, ids, mods = module_streams(folder)
    for stream in (region, probes):
        require(
            len(stream) == len(metrics) and np.array_equal(stream["tick"], np.arange(len(metrics))),
            "stream timeline",
        )
        require(np.isfinite(stream["values"]).all(), "finite stream")
    require(np.min(region["values"]) >= 0, "nonnegative shell energies/statistics")
    initial = q.checkpoint(root, stage, seed, signal, 0)
    e0 = sum(q.partitions(initial["palette"], initial["u"], initial["v"])[3])
    require(abs(e0 - float(params["initial_energy"])) <= 1e-12, "initial actual energy")
    require(e0 == 0 if signal == "ZERO" else abs(e0 - 1) <= 1e-12, "energy1/zero")
    require(int(params["port_a"]) == 2182 and int(params["port_b"]) == 2186, "physical ports")
    amplitudes = (float(params["amplitude_a"]), float(params["amplitude_b"]))
    expected = np.zeros((4096, 64))
    expected[2182, initial["module"]], expected[2186, initial["module"]] = amplitudes
    require(
        np.array_equal(initial["u"].reshape(4096, 64), expected)
        and not np.count_nonzero(initial["v"]),
        "exact initial physical support",
    )
    require(initial["amplitudes"] == amplitudes, "actual amplitude header")
    unit = np.sign(expected).reshape(4096, 8, 8)
    unit_energy = sum(q.partitions(initial["palette"], unit, np.zeros_like(unit))[3])
    require(abs(unit_energy - float(params["unit_energy"])) <= 1e-12, "unit pattern energy")
    if signal != "ZERO":
        scale = math.sqrt(1 / unit_energy)
        require(
            np.allclose(expected, np.sign(expected) * scale, rtol=1e-12, atol=1e-15),
            "equal-energy amplitude policy",
        )
    maximum = 0.0
    for tick, row in enumerate(metrics):
        x = {key: float(value) for key, value in row.items()}
        require(
            all(math.isfinite(v) for v in x.values())
            and int(row["tick"]) == tick
            and abs(x["time"] - tick * dt) < 1e-9,
            "global timeline/finite",
        )
        require(
            x["forcing_work"] == 0 and x["switch_work"] == 0,
            "no continuing drive or adaptation work",
        )
        total = sum(x[key] for key in ("kinetic", "onsite", "coupling"))
        drift = abs(total - e0 + x["loss"] + x["boundary_loss"]) / max(e0, 1e-12)
        require(abs(drift - x["drift"]) <= 1e-11 and drift <= 0.01, "1 percent drift")
        require(0 <= x["peak"] <= 100 and 0 <= x["velocity_peak"] <= 100, "bounds")
        require(
            np.allclose(
                region["values"][tick, :, 2],
                region["values"][tick, :, 1] / total if total else 0,
                rtol=1e-12,
                atol=1e-15,
            ),
            "retained-energy fraction",
        )
        if signal == "ZERO":
            require(
                all(value == 0 for key, value in x.items() if key not in ("tick", "time"))
                and not np.count_nonzero(region["values"][tick])
                and not np.count_nonzero(probes["values"][tick]),
                "all-tick exact zero",
            )
        maximum = max(maximum, drift)
    frames = []
    hashes = []
    require(len(list(folder.glob("*.q8f"))) == 6, "checkpoint coverage")
    for physical_time in (0, *q.TIMES):
        frame = q.checkpoint(root, stage, seed, signal, physical_time)
        hashes.append(frame["sha256"])
        require(
            frame["seed"] == seed
            and frame["dt"] == dt
            and frame["signal"] == signal
            and frame["amplitudes"] == amplitudes,
            "checkpoint identity",
        )
        require(np.array_equal(frame["palette"], initial["palette"]), "frozen P")
        k, p, motion, components = q.partitions(frame["palette"], frame["u"], frame["v"])
        for measured, stored in ((k, frame["k"]), (p, frame["q"])):
            require(
                q.relative(measured, stored) <= 1e-12
                and float(np.abs(measured - stored).max()) <= 1e-12
                and float(np.abs(measured - stored).sum()) <= 1e-10,
                "independent full module partition",
            )
        row = metrics[frame["tick"]]
        require(
            np.allclose(
                components,
                [float(row[key]) for key in ("kinetic", "onsite", "coupling")],
                rtol=1e-12,
                atol=1e-12,
            ),
            "global independent energy",
        )
        total = sum(components)
        e = k + p
        other = e.copy().reshape(4096, 64)
        other[:, frame["module"]] = 0
        other = other.reshape(4096, 8, 8)
        other_m = motion.copy().reshape(4096, 64)
        other_m[:, frame["module"]] = 0
        other_m = other_m.reshape(4096, 8, 8)
        cross = e.copy().reshape(4096, 64)
        cross[:, [9, 27]] = 0
        cross = cross.reshape(4096, 8, 8)
        cross_m = motion.copy().reshape(4096, 64)
        cross_m[:, [9, 27]] = 0
        cross_m = cross_m.reshape(4096, 8, 8)
        expected_regions = np.array(
            [
                region_values(e, motion, other, other_m, cross, cross_m, total, name)
                for name in REGIONS
            ]
        )
        require(
            np.allclose(expected_regions, region["values"][frame["tick"]], rtol=2e-12, atol=1e-14),
            "independent shell membership and statistics",
        )
        neuron = e.sum(axis=(1, 2))
        neuron_motion = motion.sum(axis=(1, 2))
        participation = total**2 / float((neuron * neuron).sum()) if total else 0.0
        active = int(np.count_nonzero(np.delete(neuron_motion, [2182, 2186]) >= 1e-8))
        globals_expected = [
            participation,
            active,
            float(other.sum()),
            float(other_m.sum()),
            float(cross.sum()),
            float(cross_m.sum()),
        ]
        require(
            np.allclose(
                globals_expected,
                [
                    float(row[key])
                    for key in (
                        "participation",
                        "active_receivers",
                        "other_energy",
                        "other_motion",
                        "cross_energy",
                        "cross_motion",
                    )
                ],
                rtol=2e-12,
                atol=1e-12,
            ),
            "global spreading measurements",
        )
        expected_probe = []
        for site in ids:
            point = [neuron[site], neuron_motion[site]]
            for module in mods:
                point.extend(
                    (
                        frame["u"].reshape(4096, 64)[site, module],
                        frame["v"].reshape(4096, 64)[site, module],
                    )
                )
            expected_probe.append(point)
        require(
            np.allclose(expected_probe, probes["values"][frame["tick"]], rtol=2e-12, atol=1e-14),
            "signed probe and neuron energy consistency",
        )
        if physical_time:
            frames.append(frame)
    features = q.extract_features(frames)
    out = root / "features" / stage / folder.name
    out.mkdir(parents=True, exist_ok=True)
    for key, x in features.items():
        require(np.isfinite(x).all(), "finite numerical observations")
        x.tofile(out / (key + ".f64"))
    summary = dict(
        seed=seed,
        signal=signal,
        dt=dt,
        frames=hashes,
        maximum_drift=maximum,
        palette_sha256=hashlib.sha256(initial["palette"].tobytes()).hexdigest(),
    )
    (out / "COMPLETE").write_text(
        "101 numeric-only feature vectors reconstructed from full observations\n"
    )
    return summary


def signed_vector(frame):
    return np.concatenate((frame["u"].ravel(), frame["v"].ravel()))


def controls(root):
    symmetry = []
    superposition = []
    refinement = {}
    for stage, seeds in (("train", q.TRAIN), ("evaluate", q.HELD), ("refine", q.HELD)):
        for seed in seeds:
            virgin = q.checkpoint(root, stage, seed, "ZERO", 0)["palette"]
            for signal in q.SIGNALS:
                require(
                    np.array_equal(q.checkpoint(root, stage, seed, signal, 0)["palette"], virgin),
                    "same morphology for paired inputs",
                )
            for positive, negative in (("S9p", "S9m"), ("S27p", "S27m")):
                errors = []
                for t in (0, *q.TIMES):
                    a = q.checkpoint(root, stage, seed, positive, t)
                    b = q.checkpoint(root, stage, seed, negative, t)
                    error = q.relative(signed_vector(a), -signed_vector(b))
                    rms = float(np.sqrt(np.mean((signed_vector(a) + signed_vector(b)) ** 2)))
                    for field in ("k", "q"):
                        require(
                            q.relative(a[field], b[field]) <= 1e-12
                            and float(np.abs(a[field] - b[field]).max()) <= 1e-12,
                            "sign-invariant module energy",
                        )
                    require(error <= 1e-12 and rms <= 1e-14, "signed inversion")
                    errors.append(error)
                pa = root / stage / f"s{seed}_{positive}"
                pb = root / stage / f"s{seed}_{negative}"
                ga, gb = rows(pa / "metrics.csv"), rows(pb / "metrics.csv")
                for key in ("kinetic", "onsite", "coupling"):
                    aa = np.array([float(r[key]) for r in ga])
                    bb = np.array([float(r[key]) for r in gb])
                    require(
                        q.relative(aa, bb) <= 1e-12 and float(np.abs(aa - bb).max()) <= 1e-12,
                        "every-tick energy inversion",
                    )
                sa = module_streams(pa)[0]["values"]
                sb = module_streams(pb)[0]["values"]
                require(
                    q.relative(sa, sb) <= 1e-12 and float(np.abs(sa - sb).max()) <= 1e-12,
                    "shell sign symmetry",
                )
                symmetry.append(
                    dict(
                        stage=stage,
                        seed=seed,
                        positive=positive,
                        maximum_signed_error=max(errors),
                        exact_energy_stream_bytes=q.sha(pa / "regions.q8r")
                        == q.sha(pb / "regions.q8r"),
                        pass_gate=True,
                    )
                )
            for signal, sign in (("ABp", 1), ("ABm", -1)):
                errors = []
                initial = q.checkpoint(root, stage, seed, signal, 0)
                a0 = q.checkpoint(root, stage, seed, "S27p", 0)
                b0 = q.checkpoint(root, stage, seed, "B27p", 0)
                alpha = initial["amplitudes"][0] / a0["amplitudes"][0]
                beta = abs(initial["amplitudes"][1]) / b0["amplitudes"][1]
                for t in (0, *q.TIMES):
                    a = q.checkpoint(root, stage, seed, "S27p", t)
                    b = q.checkpoint(root, stage, seed, "B27p", t)
                    target = signed_vector(q.checkpoint(root, stage, seed, signal, t))
                    expected = alpha * signed_vector(a) + sign * beta * signed_vector(b)
                    error = q.relative(target, expected)
                    rms = float(np.sqrt(np.mean((target - expected) ** 2)))
                    require(error <= 1e-12 and rms <= 1e-14, "matched signed superposition")
                    errors.append(error)
                superposition.append(
                    dict(
                        stage=stage,
                        seed=seed,
                        signal=signal,
                        alpha=alpha,
                        beta=beta,
                        maximum_error=max(errors),
                        pass_gate=True,
                    )
                )
    for seed in q.HELD:
        for signal in q.SIGNALS:
            errors = []
            for t in q.TIMES:
                a = q.checkpoint(root, "evaluate", seed, signal, t)
                b = q.checkpoint(root, "refine", seed, signal, t)
                errors.append(q.relative(signed_vector(a), signed_vector(b)))
                require(np.array_equal(a["palette"], b["palette"]), "frozen cross-grid morphology")
            refinement[f"{seed}/{signal}"] = dict(
                seed=seed,
                signal=signal,
                errors=errors,
                maximum_error=max(errors),
                pass_gate=max(errors) <= 0.015,
            )
    return symmetry, superposition, refinement


def transport(root, refinement):
    propagation = []
    spreading = []
    arrivals = []
    for seed in q.HELD:
        for signal in q.SIGNALS[:6]:
            per_grid = []
            for stage in ("evaluate", "refine"):
                folder = root / stage / f"s{seed}_{signal}"
                dt = float(rows(folder / "parameters.csv")[0]["dt"])
                stream = module_streams(folder)[0]
                region_results = {}
                for ri, name in enumerate(REGIONS):
                    dynamic = stream["values"][:, ri, 3]
                    local = stream["values"][:, ri, 1]
                    crossed = np.nonzero(dynamic >= 1e-8)[0]
                    total_crossed = np.nonzero(local >= 1e-8)[0]
                    peak = int(np.argmax(dynamic))
                    values = dict(
                        stage=stage,
                        seed=seed,
                        signal=signal,
                        region=name,
                        arrival=float(crossed[0] * dt) if len(crossed) else None,
                        total_arrival=float(total_crossed[0] * dt) if len(total_crossed) else None,
                        peak=float(dynamic[peak]),
                        peak_time=float(peak * dt),
                        initial_mechanical=float(local[0]),
                    )
                    arrivals.append(values)
                    region_results[name] = values
                metrics = rows(folder / "metrics.csv")
                passing = []
                for t in q.TIMES:
                    row = metrics[round(t / dt)]
                    e = sum(float(row[k]) for k in ("kinetic", "onsite", "coupling"))
                    if (
                        float(row["participation"]) >= 8
                        and float(row["active_receivers"]) >= 8
                        and float(row["other_motion"]) / max(e, 1e-30) >= 0.01
                    ):
                        passing.append(t)
                per_grid.append((region_results, passing))
            valid = refinement[f"{seed}/{signal}"]["pass_gate"]
            spreading.append(
                dict(
                    seed=seed,
                    signal=signal,
                    passing_times_coarse=per_grid[0][1],
                    passing_times_fine=per_grid[1][1],
                    verdict="INDETERMINATE"
                    if not valid
                    else "PASS"
                    if all(r[1] for r in per_grid)
                    else "FAIL",
                )
            )
            if signal in q.SIGNALS[:4]:
                for d in q.DISTANCES:
                    a, b = [r[0][f"A{d}"] for r in per_grid]
                    ordered = all(
                        r[0][f"A{d}"]["arrival"] is not None
                        and (
                            d == 1
                            or (
                                r[0][f"A{q.DISTANCES[q.DISTANCES.index(d) - 1]}"]["arrival"]
                                is not None
                                and r[0][f"A{d}"]["arrival"]
                                >= r[0][f"A{q.DISTANCES[q.DISTANCES.index(d) - 1]}"]["arrival"]
                            )
                        )
                        for r in per_grid
                    )
                    peak_error = abs(a["peak"] - b["peak"]) / max(b["peak"], 1e-30)
                    arrival_error = (
                        abs(a["arrival"] - b["arrival"])
                        if a["arrival"] is not None and b["arrival"] is not None
                        else None
                    )
                    passed = (
                        ordered
                        and peak_error <= 0.05
                        and arrival_error is not None
                        and arrival_error <= 0.1 + 1e-12
                    )
                    propagation.append(
                        dict(
                            seed=seed,
                            signal=signal,
                            distance=d,
                            arrival_coarse=a["arrival"],
                            arrival_fine=b["arrival"],
                            peak_relative_error=peak_error,
                            arrival_disagreement=arrival_error,
                            verdict="INDETERMINATE" if not valid else "PASS" if passed else "FAIL",
                        )
                    )
    return propagation, spreading, arrivals


def combine_verdict(items):
    return "INDETERMINATE" if "INDETERMINATE" in items else "FAIL" if "FAIL" in items else "PASS"


def finalize(root, summaries):
    symmetry, superposition, refinement = controls(root)
    models, predictions = q.evaluate(root, refinement)
    propagation, spreading, arrivals = transport(root, refinement)

    def model(pair, key):
        return next(m for m in models if m["pair"] == pair and m["key"] == key)

    p4 = combine_verdict(
        [model(pair, f"A{d}_all_UV")["verdict"] for pair in ("SIGN9", "SIGN27") for d in (2, 4)]
    )
    invariant = all(
        not any(x["detected"] for x in m["margins"])
        for m in models
        if m["pair"] in ("SIGN9", "SIGN27") and m["rep"] in ("G", "T", "KP", "SH")
    )
    require(invariant, "quadratic representation unexpectedly distinguishes full sign inversion")
    repeat_folder = root / "repeat/s107_ABm"
    files = []
    for p in sorted(repeat_folder.iterdir()):
        require(q.sha(p) == q.sha(root / "train/s107_ABm" / p.name), "exact raw repeat")
        files.append(p.name)
    verdicts = dict(
        P1=combine_verdict([r["verdict"] for r in propagation]),
        P2=combine_verdict([r["verdict"] for r in spreading]),
        P3={f"A{d}": model("LOC", f"A{d}_all_T")["verdict"] for d in (2, 4, 6)},
        P4=p4,
        P5={f"F{d}": model("DUAL", f"F{d}_all_T")["verdict"] for d in (2, 4, 6)},
        P6="PASS" if all(r["pass_gate"] for r in refinement.values()) else "FAIL",
    )
    result = dict(
        schema=1,
        source_sha256=SOURCE_SHA,
        actual_cases=len(summaries),
        repeat_files=files,
        trajectories=summaries,
        symmetry=symmetry,
        superposition=superposition,
        refinement=refinement,
        propagation=propagation,
        spreading=spreading,
        arrivals=arrivals,
        decoders=models,
        predictions=predictions,
        verdicts=verdicts,
    )
    (root / "verification.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("SCIENTIFIC VERDICTS", json.dumps(verdicts), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--follow", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    root = args.root
    cache = root / "audit"
    cache.mkdir(exist_ok=True)
    summaries = {}
    while True:
        changed = False
        for stage in ("train", "evaluate", "refine", "repeat"):
            folder = root / stage
            if not folder.exists():
                continue
            for case in sorted(folder.iterdir()):
                if not case.is_dir() or not (case / "COMPLETE").exists():
                    continue
                key = stage + "/" + case.name
                if key in summaries:
                    continue
                inputs = {p.name: q.sha(p) for p in sorted(case.iterdir()) if p.is_file()}
                target = cache / (stage + "_" + case.name + ".json")
                old = json.loads(target.read_text()) if target.exists() else {}
                if (
                    not args.fresh
                    and old.get("source_sha256") == SOURCE_SHA
                    and old.get("inputs") == inputs
                ):
                    summary = old["summary"]
                    q.CHECKED.update(summary["frames"])
                else:
                    summary = audit_case(root, stage, case)
                    target.write_text(
                        json.dumps(
                            dict(source_sha256=SOURCE_SHA, inputs=inputs, summary=summary), indent=2
                        )
                        + "\n"
                    )
                summaries[key] = summary
                changed = True
                print("AUDITED", key, flush=True)
        counts = {
            stage: sum(k.startswith(stage + "/") for k in summaries)
            for stage in ("train", "evaluate", "refine", "repeat")
        }
        (root / "audit-progress.json").write_text(
            json.dumps(dict(counts=counts, source_sha256=SOURCE_SHA), indent=2) + "\n"
        )
        if counts["train"] == 32 and not (cache / "TRAIN_READY").exists():
            (cache / "TRAIN_READY").write_text(SOURCE_SHA + "\n")
        if counts == dict(train=32, evaluate=32, refine=32, repeat=1):
            break
        if not args.follow:
            raise ValueError("matrix incomplete; --follow awaits completed cases")
        if not changed:
            time.sleep(2)
    finalize(root, summaries)


if __name__ == "__main__":
    main()
