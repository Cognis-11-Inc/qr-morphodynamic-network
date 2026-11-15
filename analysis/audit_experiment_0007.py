"""Independent QR7 measurement audit and portable evidence export.

May follow the serial engine as trajectories finish. Caches bind the checker
sources and every input byte; changing either forces revalidation.
"""

import argparse
import csv
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

from analysis import experiment_0007 as q7
from analysis.experiment_0005 import energy, fnv, require, rows
from analysis.experiment_0006 import internal, morph, scores_from_history, variant

PROBES = [0, 2182, 2183, 2184, 2186, 2191]
SOURCE = b"".join(
    Path(p).read_bytes()
    for p in (
        __file__,
        "analysis/experiment_0007.py",
        "analysis/experiment_0006.py",
        "analysis/experiment_0005.py",
    )
)
SOURCE_SHA = hashlib.sha256(SOURCE).hexdigest()


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def input_hashes(folder):
    return {p.name: sha(p) for p in sorted(folder.iterdir()) if p.is_file()}


def fingerprint(frame):
    """All physical initial fields and histories/audits in Rust fingerprint order."""
    b = bytearray(frame["palette"].tobytes())
    b.extend(frame["u"].tobytes())
    b.extend(frame["v"].tobytes())
    b.extend(bytes(2 * q7.FIELDS * 8))  # Initial V/H, reset exactly to zero.
    b.extend(np.array([frame["dt"], 0.0, 0.0, 0.0, 0.0], dtype="<f8").tobytes())
    b.extend((0).to_bytes(8, "little"))
    return fnv(b)


def audit_history(folder, before, post, params, derived):
    velocity, history, scores = [
        np.fromfile(folder / f"{name}.f64", "<f8").reshape(4096, 64)
        for name in ("velocity-history", "shape-history", "scores")
    ]
    require(
        all(np.isfinite(a).all() and np.min(a) >= 0 for a in (velocity, history, scores)),
        "history finite positive",
    )
    require(
        np.allclose(scores_from_history(history), scores, rtol=1e-14, atol=1e-300),
        "local eligibility",
    )
    data = (folder / "early.q7p").read_bytes()
    require(data[:8] == b"QR7PRB01", "write probe schema")
    dtype = np.dtype([("tick", "<u8"), ("state", "<f8", (6, 64, 2))])
    require((len(data) - 8) % dtype.itemsize == 0, "write probe length")
    samples = np.frombuffer(data, dtype=dtype, offset=8)
    dt = float(params["dt"])
    require(len(samples) == round(8 / dt) + 1, "write probe horizon")
    require(np.array_equal(samples["tick"], np.arange(len(samples))), "write probe timeline")
    u, v = samples["state"][..., 0], samples["state"][..., 1]
    require(np.isfinite(u).all() and np.isfinite(v).all(), "write probe finite")
    strain = np.empty_like(u)
    for module in range(64):
        strain[:, :, module] = np.mean(
            (u[:, :, module, None] - u[:, :, internal(module)]) ** 2, axis=2
        )
    weights = np.ones(len(samples))
    weights[[0, -1]] = 0.5
    cv = np.sum(v * v * weights[:, None, None], axis=0) * dt
    ch = np.sum((v * v + 0.25 * strain) * weights[:, None, None], axis=0) * dt
    require(np.allclose(cv, velocity[PROBES], rtol=2e-12, atol=1e-300), "independent V quadrature")
    require(np.allclose(ch, history[PROBES], rtol=2e-12, atol=1e-300), "independent H quadrature")
    commit = rows(folder / "commit.csv")[0]
    frozen, quiet = commit["frozen"] == "true", commit["quiet"] == "true"
    rule = int(params["rule"])
    expected = before if frozen else morph(before, velocity, scores, rule)
    require(np.array_equal(post, expected), "independent complete registered edit decisions")
    changed = before != post
    counts = np.count_nonzero(changed, axis=1)
    require(int(counts.max()) <= 8, "per-neuron edit cap")
    if rule == 3:
        require(
            np.array_equal(np.sort(before, axis=1), np.sort(post, axis=1)),
            "R3 histogram preservation",
        )
    if quiet or frozen:
        require(not np.any(changed), "zero/frozen changes")
    if quiet:
        require(np.count_nonzero(history) == 0 and np.count_nonzero(velocity) == 0, "quiet history")
    edits = rows(folder / "edits.csv")
    actual = {(int(r["id"]), int(r["module"])) for r in edits}
    require(
        actual == set(zip(*np.nonzero(changed), strict=True)) and len(edits) == len(actual),
        "actual edit ledger",
    )
    for r in edits:
        i, m = int(r["id"]), int(r["module"])
        require(int(r["before"]) == before[i, m] and int(r["after"]) == post[i, m], "edit colors")
    # Complete eligibility/rank table is portable; raw H/V/S remain external records.
    derived.mkdir(parents=True, exist_ok=True)
    ranks = np.argsort(np.argsort(-scores, axis=1, kind="stable"), axis=1, kind="stable")
    eligible = (scores >= 1e-8) & (scores >= 0.05 * np.max(scores, axis=1)[:, None])
    with gzip.open(derived / "eligibility.csv.gz", "wt", compresslevel=5) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ("id", "module", "V", "H", "S", "rank", "eligible", "chosen", "before", "after")
        )
        for i in range(4096):
            for m in range(64):
                writer.writerow(
                    (
                        i,
                        m,
                        format(velocity[i, m], ".17e"),
                        format(history[i, m], ".17e"),
                        format(scores[i, m], ".17e"),
                        int(ranks[i, m]),
                        int(eligible[i, m]),
                        int(changed[i, m]),
                        int(before[i, m]),
                        int(post[i, m]),
                    )
                )
    distance = np.array(
        [
            abs(i % 16 - 2182 % 16)
            + abs(i // 16 % 16 - 2182 // 16 % 16)
            + abs(i // 256 - 2182 // 256)
            for i in range(4096)
        ]
    )
    return dict(
        edits=int(changed.sum()),
        neurons=int(np.count_nonzero(counts)),
        remote_edits=int(np.delete(counts, [2182, 2183]).sum()),
        max_distance=int(distance[counts > 0].max()) if np.any(counts) else 0,
        frozen=frozen,
        quiet=quiet,
    )


def audit_run(stage, folder, derived):
    params = rows(folder / "parameters.csv")[0]
    write = params["operation"] == "Write"
    dt = float(params["dt"])
    end = 8 if write else 32
    metrics = rows(folder / "metrics.csv")
    require(len(metrics) == round(end / dt) + 1, "all tick diagnostics")
    initial = q7.checkpoint(stage, folder.name, 0)
    p = initial["palette"]
    flat = p.reshape(4096, 64)
    e0 = sum(energy(p, initial["u"], initial["v"])[:3])
    amplitude = float(params["amplitude"])
    require(abs(e0 - float(params["initial_energy"])) <= 1e-12, "independent initial energy")
    require(e0 == 0 if amplitude == 0 else abs(e0 - 1) <= 1e-12, "equal energy / exact quiet")
    expected_u = np.zeros((4096, 64))
    expected_u[int(params["port"]), int(params["module"])] = amplitude
    require(
        np.array_equal(expected_u.reshape(4096, 8, 8), initial["u"])
        and not np.count_nonzero(initial["v"]),
        "exact reset impulse",
    )
    require(
        fingerprint(initial) == int(params["initial_fingerprint"]),
        "independent initial state fingerprint",
    )
    maximum = 0.0
    for tick, row in enumerate(metrics):
        x = {key: float(value) for key, value in row.items()}
        require(all(math.isfinite(value) for value in x.values()), "finite diagnostics")
        require(
            int(row["tick"]) == tick and abs(x["time"] - tick * dt) < 1e-9, "exact all-tick times"
        )
        total = sum(x[k] for k in ("kinetic", "onsite", "coupling"))
        drift = abs(total - e0 + x["loss"] + x["boundary_loss"] - x["switch_work"]) / max(e0, 1e-12)
        require(abs(drift - x["drift"]) <= 1e-11 and drift <= 0.01, "one percent drift")
        require(0 <= x["peak"] <= 100 and 0 <= x["velocity_peak"] <= 100, "all-tick bounds")
        if amplitude == 0:
            require(total == x["peak"] == x["velocity_peak"] == 0, "quiet all-tick zero")
        maximum = max(maximum, drift)
    trace = np.fromfile(folder / "outputs.f64", "<f8").reshape(-1, 12)
    require(len(trace) == len(metrics) and np.isfinite(trace).all(), "every tick signed outputs")
    wanted = (0, 8) if write else (0, *q7.TIMES)
    hashes = []
    require(len(list(folder.glob("[0-9]*.q7f"))) == len(wanted), "signed checkpoint coverage")
    for time_value in wanted:
        f = q7.checkpoint(stage, folder.name, time_value)
        hashes.append(f["sha256"])
        require(
            f["seed"] == int(params["seed"])
            and f["module"] == int(params["module"])
            and f["port"] == int(params["port"])
            and f["rule"] == int(params["rule"]),
            "truthful checkpoint metadata",
        )
        require(np.array_equal(f["palette"], p), "frozen trajectory palette")
        measured = energy(p, f["u"], f["v"])
        row = metrics[f["tick"]]
        for key, value in zip(("kinetic", "onsite", "coupling"), measured[:3], strict=True):
            require(abs(value - float(row[key])) <= 1e-10, "independent checkpoint energy")
        sample = np.array(
            [
                f[field].reshape(4096, 64)[site, module]
                for site in q7.OUTPUTS
                for module in (9, 27)
                for field in ("u", "v")
            ]
        )
        require(np.array_equal(sample, trace[f["tick"]]), "signed trace checkpoint")
    receipt = (folder / "RESET").read_text()
    require("zero=true\npalette_retained=true\n" in receipt, "exact reset receipt")
    summary = dict(
        id=folder.name,
        write=write,
        seed=int(params["seed"]),
        rule=int(params["rule"]),
        max_energy_drift=maximum,
        frames=hashes,
        initial_energy=e0,
    )
    if write:
        pre = q7.checkpoint(stage, folder.name, 8)
        post = q7.decode(folder / "post.q7f")
        hashes.append(post["sha256"])
        require(
            np.array_equal(pre["u"], post["u"]) and np.array_equal(pre["v"], post["v"]),
            "no transient commit jump",
        )
        before_e = energy(p, pre["u"], pre["v"])
        after_e = energy(post["palette"], post["u"], post["v"])
        work = rows(folder / "switch.csv")
        require(len(work) == 4096, "complete per-neuron switching work")
        for i, row in enumerate(work):
            require(
                int(row["id"]) == i
                and abs(float(row["pre"]) - before_e[3][i]) < 1e-11
                and abs(float(row["post"]) - after_e[3][i]) < 1e-11
                and abs(float(row["work"]) - (after_e[3][i] - before_e[3][i])) < 1e-11,
                "independent local switch work",
            )
        delta = sum(after_e[:3]) - sum(before_e[:3])
        commit = rows(folder / "commit.csv")[0]
        require(abs(delta - float(commit["switch_work"])) < 1e-10, "explicit total switching work")
        require(
            f"palette_fnv={fnv(post['palette'].tobytes())}\n" in receipt,
            "persistent committed palette after reset",
        )
        summary.update(
            audit_history(folder, flat, post["palette"].reshape(4096, 64), params, derived)
        )
        summary["switch_work"] = delta
    else:
        require(f"palette_fnv={fnv(p.tobytes())}\n" in receipt, "read reset retains P")
        features = np.fromfile(folder / "features.f64", "<f8")
        selected = np.concatenate([trace[round(t / dt)] for t in q7.TIMES])
        require(np.array_equal(features, selected), "numeric-only signed read features")
    return summary


def controls(stage):
    results = []
    ledger = rows(stage / "ledger.csv")
    for row in ledger:
        if row["kind"] not in q7.CONTROLS:
            continue
        name, seed, rule, symbol, kind = (
            row["id"],
            int(row["seed"]),
            int(row["rule"]),
            int(row["symbol"]),
            row["kind"],
        )
        base = q7.checkpoint(stage, f"s{seed}_CALIBRATE_p9", 0)["palette"].reshape(4096, 64)
        after = q7.decode(stage / q7.ident(seed, rule, symbol, "WRITE") / "post.q7f")[
            "palette"
        ].reshape(4096, 64)
        expected = base.copy()
        if kind == "ALL":
            expected = after.copy()
        elif kind == "WRITE_PORT_ONLY":
            expected[2182] = after[2182]
        elif kind == "READ_PORT_ONLY":
            expected[2183] = after[2183]
        elif kind == "REMOTE_ONLY":
            expected = after.copy()
            expected[[2182, 2183]] = base[[2182, 2183]]
        elif kind == "SHUFFLED":
            expected = variant(base, after, "SHUFFLE_POSITION", rule, seed)
            require(
                np.array_equal(
                    np.count_nonzero(expected != base, axis=1),
                    np.count_nonzero(after != base, axis=1),
                ),
                "shuffled per-neuron edit count",
            )
        for pulse in (9, 27):
            f = q7.checkpoint(stage, f"{name}_p{pulse}", 0)
            require(
                np.array_equal(f["palette"].reshape(4096, 64), expected),
                "registered distributed causal control",
            )
        q7.feature(stage, name)
        results.append(dict(id=name, kind=kind, pass_gate=True))
    return results


def repeat(root):
    base, again = root / "train", root / "repeat"
    require((again / "COMPLETE").exists(), "repeat complete")
    files = 0
    for folder in sorted(again.iterdir()):
        if folder.is_dir():
            original = base / folder.name
            for file in sorted(folder.iterdir()):
                require(
                    file.is_file() and sha(file) == sha(original / file.name),
                    "byte-identical repeat " + str(file),
                )
                files += 1
    return dict(pass_gate=True, identical_files=files, seed=31, rule=2, symbol=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    root = args.root
    cache = root / "audit"
    cache.mkdir(exist_ok=True)
    summaries = {}
    while True:
        changed = False
        for stage_name in ("train", "evaluate", "refine"):
            stage = root / stage_name
            if not stage.exists():
                continue
            for folder in sorted(stage.iterdir()):
                if not folder.is_dir() or not (folder / "COMPLETE").exists():
                    continue
                key = stage_name + "/" + folder.name
                if key in summaries:
                    continue
                hashes = input_hashes(folder)
                target = cache / f"{stage_name}_{folder.name}.json"
                stored = json.loads(target.read_text()) if target.exists() else {}
                if stored.get("source_sha256") == SOURCE_SHA and stored.get("inputs") == hashes:
                    summary = stored["summary"]
                    q7.CHECKED.update(summary["frames"])
                else:
                    summary = audit_run(stage, folder, root / "derived" / stage_name / folder.name)
                    target.write_text(
                        json.dumps(
                            dict(source_sha256=SOURCE_SHA, inputs=hashes, summary=summary), indent=2
                        )
                        + "\n"
                    )
                summaries[key] = summary
                changed = True
                print("AUDITED", key, flush=True)
        (root / "audit-progress.json").write_text(
            json.dumps(dict(source_sha256=SOURCE_SHA, trajectories=len(summaries)), indent=2) + "\n"
        )
        if (root / "repeat/COMPLETE").exists():
            break
        if not args.follow:
            require(False, "measurement matrix incomplete; use --follow to await serial engine")
        if not changed:
            time.sleep(2)
    counts = {
        name: sum(1 for k in summaries if k.startswith(name + "/"))
        for name in ("train", "evaluate", "refine")
    }
    require(
        counts == dict(train=208, evaluate=208, refine=80), "registered actual trajectory matrix"
    )
    causal = {name: controls(root / name) for name in ("train", "evaluate", "refine")}
    for name, seeds in (("train", q7.TRAIN), ("evaluate", q7.HELD), ("refine", q7.HELD)):
        for seed in seeds:
            q7.feature(root / name, f"s{seed}_CALIBRATE")
    readout = q7.analyse(root)
    structure = []
    for name, seeds in (("train", q7.TRAIN), ("evaluate", q7.HELD), ("refine", q7.HELD)):
        for seed in seeds:
            for rule in (2, 3):
                palettes = [
                    q7.decode(root / name / q7.ident(seed, rule, s, "WRITE") / "post.q7f")[
                        "palette"
                    ]
                    for s in (0, 1)
                ]
                structure.append(
                    dict(stage=name, seed=seed, rule=rule, distinct=not np.array_equal(*palettes))
                )
    structural_pass = all(r["distinct"] for r in structure) and all(
        r["edit_jaccard"] >= 0.9 for r in readout["remote_influence"]
    )
    for model in readout["models"]:
        model["operational_pass"] &= all(
            r["distinct"] for r in structure if r["rule"] == model["rule"]
        ) and all(
            r["edit_jaccard"] >= 0.9
            for r in readout["remote_influence"]
            if r["rule"] == model["rule"]
        )
    result = dict(
        source_sha256=SOURCE_SHA,
        actual_counts=counts,
        logical_trajectories=688,
        reused_trajectories=192,
        repeat=repeat(root),
        physical_audit_pass=True,
        structural_pass=structural_pass,
        structure=structure,
        trajectories=summaries,
        causal_controls=causal,
        readout=readout,
    )
    (root / "verification.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("COMPLETE: independently verified", counts, flush=True)
    for model in readout["models"]:
        print("MODEL", model, flush=True)


if __name__ == "__main__":
    main()
